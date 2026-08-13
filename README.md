# Griductive - Game suy luận logic không đoán

Griductive là game phá án trên một bảng nhân vật, trong đó mỗi người bí mật là **Criminal** hoặc **Innocent**. Người chơi phải đọc các manh mối đang công khai, chứng minh từng kết luận bằng logic và lần lượt lật toàn bộ thẻ nhân vật.

Điểm đặc biệt của Griductive là **không cho phép đoán**. Một lựa chọn chỉ được chấp nhận khi trạng thái của nhân vật là hệ quả bắt buộc từ Knowledge Base hiện tại. Game sử dụng biểu diễn logic mệnh đề, mã hóa CNF và SAT solver DPLL được tự cài đặt bằng Python.

## Hình ảnh và phong cách

Game sử dụng giao diện desktop theo phong cách cozy mystery:

- Bộ 25 chân dung nhân vật minh họa nguyên bản.
- Thẻ nhân vật hiển thị tên, nghề nghiệp và tọa độ.
- Thẻ được lật sẽ chuyển thành thẻ manh mối.
- Màu xanh biểu thị Innocent và màu đỏ biểu thị Criminal.
- Chữ, portrait, padding và vùng xuống dòng tự điều chỉnh theo kích thước cửa sổ.

## Luật chơi

Mỗi ván bắt đầu với hai thẻ đã được công khai. Trạng thái và manh mối trên hai thẻ này tạo thành thông tin ban đầu.

1. Đọc các manh mối đang hiển thị.
2. Chọn một thẻ nhân vật chưa được giải.
3. Chọn `INNOCENT` hoặc `CRIMINAL` nếu thông tin hiện tại chứng minh được kết luận đó.
4. Nếu lựa chọn hợp lệ, thẻ được lật và manh mối mới được thêm vào Knowledge Base.
5. Tiếp tục suy luận cho tới khi xác định được toàn bộ nhân vật.

Mọi manh mối được công khai đều đúng, bất kể người sở hữu manh mối là Criminal hay Innocent.

### Phản hồi verdict

- `ACCEPTED`: kết luận đã được chứng minh; thẻ được lật và clue mới xuất hiện.
- `NOT_PROVABLE`: cả hai trạng thái vẫn có thể xảy ra với thông tin hiện tại.
- `CONTRADICTED`: trạng thái ngược lại đã được logic chứng minh.
- `INCONSISTENT`: Knowledge Base không còn mô hình thỏa mãn.

Verdict bị từ chối không làm thay đổi ván chơi và không tiết lộ manh mối ẩn.

## Puzzle ngẫu nhiên

Game không sử dụng các map cố định. Khi mở game hoặc bấm `New Random Case`, hệ thống tự tạo một case mới:

- Số hàng và số cột được chọn độc lập từ 3 đến 5.
- Hỗ trợ đủ chín kích thước từ 3x3 đến 5x5, bao gồm bảng chữ nhật như 3x5 hoặc 5x4.
- Nhân vật, portrait, nghề nghiệp và vị trí trên bảng được xáo trộn.
- Trạng thái bí mật, loại clue, thẻ mở đầu và reveal chain được sinh lại.
- Mỗi puzzle có đúng một lời giải hoàn chỉnh.
- Mọi puzzle đều có thể giải tuần tự mà không cần đoán.

Mỗi case có một seed hệ hexadecimal hiển thị trên thanh trên cùng. `Replay Seed` cho phép nhập lại seed để tái tạo chính xác một ván cũ, thuận tiện cho demo, kiểm thử và sửa lỗi.

## Các loại manh mối

Sáu clue lõi:

- `FACT`: một người có trạng thái xác định.
- `SAME`: hai người có cùng trạng thái.
- `DIFFERENT`: hai người có trạng thái khác nhau.
- `EXACTLY`: chính xác `k` Criminal trong một vùng.
- `AT_LEAST`: ít nhất `k` Criminal trong một vùng.
- `AT_MOST`: nhiều nhất `k` Criminal trong một vùng.

Hai clue mở rộng:

- `PARITY`: số Criminal trong vùng là chẵn hoặc lẻ.
- `COUNT_COMPARE`: so sánh số Criminal giữa hai vùng.

Các vùng có thể là hàng, cột, hàng xóm tám hướng hoặc danh sách ô cụ thể.

## Tính năng

### New Random Case

Tạo một puzzle mới với kích thước, roster, vị trí, trạng thái và clue chain mới.

### Restart

Đưa case hiện tại về trạng thái ban đầu. Seed và nội dung puzzle được giữ nguyên, còn timer, trace, spotlight và pencil marks được xóa.

### Replay Seed

Tái tạo chính xác một puzzle từ seed hexadecimal của case.

### Clue Spotlight

Bấm vào một thẻ đã giải để xem phạm vi clue:

- Viền vàng: người sở hữu clue.
- Viền xanh: các nhân vật hoặc ô được clue nhắc tới.
- Các thẻ không liên quan được làm mờ.

### Pencil Mark

Chọn một thẻ chưa giải và bấm `Mark` để luân phiên qua năm màu ghi chú. Pencil marks chỉ hỗ trợ người chơi tổ chức suy nghĩ và không bao giờ được đưa vào Knowledge Base.

### Hint hai giai đoạn

- Lần bấm đầu tiên spotlight một clue công khai có liên quan.
- Lần bấm tiếp theo chỉ ra nhân vật và verdict có thể chứng minh.

Hint chỉ nhận public state và không đọc hidden solution.

### Auto Solve

Agent tự động kiểm tra entailment, chọn verdict bắt buộc theo thứ tự xác định, lật từng thẻ và tiếp tục tới khi case được giải. Quá trình không sử dụng phỏng đoán.

### Deduction Trace và Solver Metrics

Giao diện hiển thị:

- Số biến chính và biến phụ.
- Số CNF clauses.
- SAT calls.
- Decisions, propagations và backtracks.
- Thời gian chạy solver.
- Danh sách từng bước suy luận và clue vừa được mở.

### Giao diện responsive

Khi thay đổi kích thước cửa sổ, game tự động đo lại vùng card và điều chỉnh:

- Kích thước font của clue.
- Chiều rộng xuống dòng.
- Kích thước portrait.
- Font tên, nghề nghiệp, trạng thái và tọa độ.
- Padding bên trong card.

Clue vẫn được hiển thị đầy đủ khi chơi ở cửa sổ nhỏ.

## Kiến trúc logic

Game tách biệt rõ hai vai trò:

- `GameEngine` sở hữu puzzle hoàn chỉnh, hidden solution và các clue chưa lật.
- `LogicAgent` chỉ nhận public state gồm clue đã công khai và verdict đã chứng minh.

Agent xây dựng Knowledge Base:

```text
KB_t = CNF(revealed clues) AND unit clauses(proved verdicts)
```

Để phân loại nhân vật `i`:

```text
KB AND NOT Ci = UNSAT  =>  CRIMINAL
KB AND Ci     = UNSAT  =>  INNOCENT
Both SAT                 =>  UNKNOWN
KB itself    = UNSAT     =>  INCONSISTENT
```

DPLL solver trong dự án tự triển khai unit propagation, conflict detection, deterministic branching, recursive backtracking và complete assignment.

## Yêu cầu hệ thống

- Python 3.10 trở lên.
- Tkinter, thường được cài sẵn cùng Python trên Windows.
- Không cần cài package bên thứ ba.

Kiểm tra phiên bản Python:

```powershell
python --version
```

## Cách tải và chạy game

Clone repository:

```powershell
git clone https://github.com/TVinhQuang/Griductive_game.git
cd Griductive_game\Source
```

Chạy game:

```powershell
python main.py
```

Nếu máy có nhiều phiên bản Python, có thể dùng:

```powershell
py -3 main.py
```

## Chạy kiểm thử

Từ thư mục `Source`:

```powershell
python -B -m unittest discover -s tests -v
```

Test suite kiểm tra:

- DPLL trên công thức SAT và UNSAT.
- Semantic evaluator khớp với CNF encoding.
- Đủ chín kích thước bảng.
- Random case có nghiệm duy nhất.
- Cùng seed sinh lại đúng cùng puzzle.
- Auto Solve hoàn thành puzzle mà không đoán.
- Logic Agent không truy cập hidden solution hoặc clue chưa lật.

## Chạy thí nghiệm

Từ thư mục `Source`:

```powershell
python experiments.py
```

Kết quả được ghi vào `Source/experiment_results.csv`, bao gồm số biến, clauses, SAT calls, decisions, propagations, backtracks, deduction steps và runtime.

## Cấu trúc thư mục

```text
Griductive_game/
├── README.md
└── Source/
    ├── main.py
    ├── experiments.py
    ├── experiment_results.csv
    ├── requirements.txt
    ├── assets/
    │   └── suspect_portraits.png
    ├── griductive/
    │   ├── agent.py
    │   ├── clues.py
    │   ├── cnf.py
    │   ├── dpll.py
    │   ├── engine.py
    │   ├── gui.py
    │   ├── models.py
    │   ├── puzzles.py
    │   └── regions.py
    └── tests/
        └── test_griductive.py
```

## Công nghệ sử dụng

- Python
- Tkinter
- Propositional Logic
- CNF Encoding
- DPLL SAT Solver
- Unittest

## Ghi chú

Dự án được xây dựng cho đồ án Griductive Solver của môn Introduction to Artificial Intelligence. Mục tiêu chính là kết hợp một game có trải nghiệm trực quan với hệ thống suy luận có thể kiểm tra, tái lập và tuyệt đối không sử dụng hidden data để đưa ra verdict.
