import itertools

class GriductiveEncoder:
    def __init__(self, board_info: dict, grid_size: int):
        """
        board_info: dict dạng {"A1": "Abel", "A2": "Bea", ...}
        Tạo mapping: Biến C_i -> index (1, 2, 3...) theo thứ tự Alphabet của tên[cite: 1].
        """
        self.grid_size = grid_size
        self.board_info = board_info
        
        # 1. Deterministic Alphabetical Variable Mapping
        names = sorted(list(self.board_info.values()))
        self.var_map = {name: idx + 1 for idx, name in enumerate(names)}
        self.name_map = {idx + 1: name for idx, name in enumerate(names)}
        
        self.primary_var_count = len(self.var_map)
        self.aux_var_counter = self.primary_var_count + 1
        
        # Grid indexing for region resolution
        self.grid = {} # "A1" -> Name
        for cell, name in board_info.items():
            self.grid[cell] = name

    def get_var(self, name: str) -> int:
        return self.var_map[name]

    def _get_new_aux_var(self) -> int:
        var = self.aux_var_counter
        self.aux_var_counter += 1
        return var

    # ================= REGION RESOLUTION =================
    def resolve_region(self, region_type: str, param: str = None) -> list:
        """ Trả về danh sách TÊN các nhân vật thuộc region được chỉ định[cite: 1]. """
        targets = []
        if region_type == "ROW":
            # param là số, vd: "1"
            targets = [name for cell, name in self.grid.items() if cell[1:] == param]
        elif region_type == "COLUMN":
            # param là chữ cái, vd: "A"
            targets = [name for cell, name in self.grid.items() if cell[0] == param]
        elif region_type == "NEIGHBORS":
            # param là cell, vd: "B2"
            col, row = param[0], int(param[1:])
            for c in range(ord(col) - 1, ord(col) + 2):
                for r in range(row - 1, row + 2):
                    n_cell = f"{chr(c)}{r}"
                    if n_cell != param and n_cell in self.grid:
                        targets.append(self.grid[n_cell])
        elif region_type == "EXPLICIT":
            # param là list string dạng "A1,B2"
            cells = param.split(',')
            targets = [self.grid[c.strip()] for c in cells if c.strip() in self.grid]
        elif region_type == "BOUNDARY": # EXTENSION 1
            max_col = chr(ord('A') + self.grid_size - 1)
            for cell, name in self.grid.items():
                if cell[0] == 'A' or cell[0] == max_col or cell[1:] == '1' or cell[1:] == str(self.grid_size):
                    targets.append(name)
        return targets

    # ================= CNF ENCODERS =================
    def encode_fact(self, name: str, is_criminal: bool):
        var = self.get_var(name)
        return [[var]] if is_criminal else [[-var]]

    def encode_same(self, name1: str, name2: str):
        v1, v2 = self.get_var(name1), self.get_var(name2)
        return [[-v1, v2], [-v2, v1]]

    def encode_different(self, name1: str, name2: str):
        v1, v2 = self.get_var(name1), self.get_var(name2)
        return [[v1, v2], [-v1, -v2]]

    def encode_implies(self, name1: str, is_criminal1: bool, name2: str, is_criminal2: bool):
        """ EXTENSION 2: Nếu name1 là is_criminal1 THÌ name2 là is_criminal2 """
        v1 = self.get_var(name1) if is_criminal1 else -self.get_var(name1)
        v2 = self.get_var(name2) if is_criminal2 else -self.get_var(name2)
        return [[-v1, v2]]

    def encode_at_least_k(self, names: list, k: int):
        if k == 0: return []
        vars_list = [self.get_var(n) for n in names]
        clauses = []
        # Tổ hợp chọn (N - k + 1) phần tử để đảm bảo không thể có (N - k + 1) phần tử cùng False
        for combo in itertools.combinations(vars_list, len(vars_list) - k + 1):
            clauses.append(list(combo))
        return clauses

    def encode_at_most_k(self, names: list, k: int):
        vars_list = [self.get_var(n) for n in names]
        clauses = []
        # Tổ hợp chọn (k + 1) phần tử, không thể có (k + 1) phần tử cùng True
        for combo in itertools.combinations(vars_list, k + 1):
            clauses.append([-v for v in combo])
        return clauses

    def encode_exactly_k_combinatorial(self, names: list, k: int):
        clauses = self.encode_at_least_k(names, k)
        clauses.extend(self.encode_at_most_k(names, k))
        return clauses

    # ================= KB BUILDER =================
    def build_kb(self, revealed_clues: list, proved_verdicts: dict) -> tuple:
        """
        Xây dựng KBt từ revealed clues và proved verdicts[cite: 1].
        Trả về (KB (List[List[int]]), dict thống kê).
        """
        kb = []
        
        # 1. Thêm Unit Clauses từ proved_verdicts[cite: 1]
        for name, is_criminal in proved_verdicts.items():
            kb.extend(self.encode_fact(name, is_criminal))
            
        # 2. Convert revealed clues sang CNF[cite: 1]
        for clue in revealed_clues:
            clue_type = clue.get("type")
            if clue_type == "SAME":
                kb.extend(self.encode_same(clue["p1"], clue["p2"]))
            elif clue_type == "DIFFERENT":
                kb.extend(self.encode_different(clue["p1"], clue["p2"]))
            elif clue_type == "IMPLIES":
                kb.extend(self.encode_implies(clue["p1"], clue["s1"], clue["p2"], clue["s2"]))
            elif clue_type in ["EXACTLY", "AT_LEAST", "AT_MOST"]:
                region_names = self.resolve_region(clue["region"], clue.get("param"))
                k = clue["k"]
                if clue_type == "EXACTLY":
                    kb.extend(self.encode_exactly_k_combinatorial(region_names, k))
                elif clue_type == "AT_LEAST":
                    kb.extend(self.encode_at_least_k(region_names, k))
                elif clue_type == "AT_MOST":
                    kb.extend(self.encode_at_most_k(region_names, k))
                    
        # Loại bỏ các clause trùng lặp
        kb_unique = [list(t) for t in set(tuple(sorted(clause)) for clause in kb)]
        
        stats = {
            "primary_vars": self.primary_var_count,
            "aux_vars": self.aux_var_counter - self.primary_var_count - 1,
            "total_clauses": len(kb_unique)
        }
        return kb_unique, stats

    # ================= DIRECT SEMANTIC EVALUATOR =================
    def direct_evaluator(self, clue: dict, assignment: dict) -> bool:
        """
        Đánh giá ngữ nghĩa trực tiếp từ assignment hoàn chỉnh mà không qua CNF[cite: 1].
        assignment: dict dạng {"Abel": True, "Bea": False, ...} (True = Criminal)
        """
        c_type = clue.get("type")
        if c_type == "FACT":
            return assignment[clue["name"]] == clue["is_criminal"]
        elif c_type == "SAME":
            return assignment[clue["p1"]] == assignment[clue["p2"]]
        elif c_type == "DIFFERENT":
            return assignment[clue["p1"]] != assignment[clue["p2"]]
        elif c_type == "IMPLIES":
            cond_met = assignment[clue["p1"]] == clue["s1"]
            return (not cond_met) or (assignment[clue["p2"]] == clue["s2"])
        
        # Đếm số lượng Criminal cho các Clue dạng đếm
        region_names = self.resolve_region(clue["region"], clue.get("param"))
        criminal_count = sum(1 for name in region_names if assignment[name])
        
        k = clue["k"]
        if c_type == "EXACTLY":
            return criminal_count == k
        elif c_type == "AT_LEAST":
            return criminal_count >= k
        elif c_type == "AT_MOST":
            return criminal_count <= k
        
        return False