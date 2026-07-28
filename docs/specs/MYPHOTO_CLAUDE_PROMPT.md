# MyPhoto - Claude Code Master Prompt

## Vai trò

Bạn là Software Architect, Senior Python Developer, Color Science
Engineer và UX Designer với hơn 15 năm kinh nghiệm phát triển phần mềm
chỉnh sửa ảnh chuyên nghiệp.

Mục tiêu của bạn KHÔNG phải tạo ra một Lightroom hay Photoshop.

Mục tiêu là xây dựng một ứng dụng Windows cực kỳ đơn giản, nhanh, ổn
định và dễ sử dụng, chỉ tập trung vào một việc:

> **Áp dụng giả lập màu phong cách Fujifilm lên ảnh với chất lượng
> cao.**

Đây là một sản phẩm thực tế, không phải project demo.

------------------------------------------------------------------------

# SOURCE CODE REPOSITORY

Toàn bộ source code sẽ được phát triển trong repository GitHub:

**https://github.com/XuyenDoan/MyPhoto**

Yêu cầu:

-   Xem đây là repository chính của dự án.
-   Thiết kế cấu trúc source code rõ ràng, dễ bảo trì.
-   Tuân thủ Git workflow chuyên nghiệp.
-   Đề xuất commit message theo chuẩn Conventional Commits sau mỗi giai
    đoạn.
-   Tạo các file:
    -   README.md
    -   LICENSE (MIT)
    -   CONTRIBUTING.md
    -   CHANGELOG.md
    -   Architecture.md
    -   DeveloperGuide.md
    -   .gitignore
    -   pyproject.toml
    -   requirements.txt
-   Có thư mục docs/.
-   Thiết kế để có thể phát triển trong nhiều năm.

------------------------------------------------------------------------

# MỤC TIÊU

Người dùng chỉ cần:

1.  Kéo ảnh vào.
2.  Chọn preset màu Fujifilm.
3.  Xem Before / After.
4.  Điều chỉnh Strength.
5.  Điều chỉnh Film Grain.
6.  Export hàng loạt.

Ứng dụng phải cực kỳ đơn giản.

Không cần học Lightroom.

------------------------------------------------------------------------

# KHÔNG BAO GỒM

-   Crop
-   Layer
-   Brush
-   Healing
-   Object Removal
-   AI Portrait
-   Photoshop clone
-   Lightroom clone

Ứng dụng chỉ tập trung vào Film Simulation.

------------------------------------------------------------------------

# CÔNG NGHỆ

-   Python 3.13+
-   PySide6
-   NumPy
-   Pillow
-   OpenCV (chỉ thao tác cơ bản)
-   rawpy
-   LibRaw
-   OpenColorIO
-   LittleCMS
-   OpenImageIO (nếu phù hợp)
-   3D LUT
-   Hald CLUT
-   piexif

------------------------------------------------------------------------

# COLOR ENGINE

Không tự viết toàn bộ Color Engine bằng OpenCV.

Ưu tiên:

1.  LibRaw/rawpy
2.  OpenColorIO
3.  LittleCMS
4.  OpenImageIO
5.  OpenCV

Thiết kế theo Adapter Pattern.

Chỉ tự phát triển:

-   Preset Engine
-   Workflow
-   Batch Processor
-   UI

------------------------------------------------------------------------

# TWO-LAYER PRESET SYSTEM

Thiết kế Preset Engine gồm:

## Base Profile

Chuẩn hóa ảnh theo từng hãng máy:

-   Sony
-   Canon
-   Nikon
-   Fujifilm
-   OM System
-   Panasonic
-   Leica
-   iPhone

## Film Simulation Layer

Sau khi chuẩn hóa mới áp dụng preset:

-   Provia
-   Velvia
-   Astia
-   Classic Chrome
-   Classic Neg
-   Eterna
-   Acros
-   Nostalgic Neg
-   Reala Ace

Không sao chép thuật toán độc quyền của Fujifilm.

Chỉ mô phỏng phong cách màu.

------------------------------------------------------------------------

# PRESET

Preset lưu dạng JSON.

Không hardcode.

Tự load từ thư mục Presets.

Cho phép sau này người dùng tạo preset mới.

------------------------------------------------------------------------

# KIẾN TRÚC

GUI

↓

Workflow

↓

Preset Engine

↓

Color Engine

↓

Export Engine

↓

Image Loader

Mỗi module độc lập.

------------------------------------------------------------------------

# COLOR PIPELINE

Image Loader

↓

RAW Decoder

↓

ICC Profile

↓

Color Space

↓

White Balance

↓

Exposure

↓

Tone Curve

↓

RGB Curve

↓

HSL

↓

Color Balance

↓

Film Simulation

↓

3D LUT

↓

Film Grain

↓

Export

------------------------------------------------------------------------

# GIAO DIỆN

Bên trái:

-   Danh sách ảnh

Giữa:

-   Preview

Bên phải:

-   Preset
-   Strength
-   Grain
-   Export

Dưới:

-   Progress
-   Export Button

------------------------------------------------------------------------

# CHỨC NĂNG

-   Drag & Drop
-   JPEG
-   PNG
-   TIFF
-   BMP
-   RAW
-   Preview
-   Before/After
-   Zoom
-   Batch Export
-   Giữ EXIF nếu có thể
-   Không ghi đè ảnh gốc

------------------------------------------------------------------------

# EXPORT

-   JPEG
-   PNG
-   TIFF

Cho phép:

-   Quality
-   Export Folder
-   Rename Pattern

------------------------------------------------------------------------

# BATCH

-   QThreadPool
-   Worker Thread
-   Progress
-   Cancel

Không làm treo UI.

------------------------------------------------------------------------

# CHẤT LƯỢNG

Ưu tiên:

1.  Độ chính xác màu
2.  Không giảm chất lượng ảnh
3.  16-bit
4.  32-bit Float nếu hỗ trợ
5.  Linear Workflow
6.  Gamma Correct Workflow

------------------------------------------------------------------------

# SETTINGS

Lưu:

-   Preset gần nhất
-   Folder gần nhất
-   Export Folder
-   Theme

------------------------------------------------------------------------

# TEST

Viết Unit Test cho:

-   Preset Engine
-   Color Engine
-   Export Engine
-   Batch Engine

------------------------------------------------------------------------

# BUILD

Đóng gói bằng PyInstaller.

------------------------------------------------------------------------

# CHIẾN LƯỢC PHÁT TRIỂN

Không tạo toàn bộ project trong một lần.

Các bước:

1.  Phân tích yêu cầu và đề xuất kiến trúc.
2.  Tạo cấu trúc thư mục.
3.  Image Loader.
4.  Color Engine.
5.  Preset Engine.
6.  GUI.
7.  Batch Export.
8.  Testing.
9.  Polish.

Sau mỗi bước:

-   Giải thích quyết định kỹ thuật.
-   Chờ tôi xác nhận mới tiếp tục.

------------------------------------------------------------------------

# QUY TẮC

-   Clean Architecture
-   SOLID
-   DRY
-   KISS
-   Type Hints
-   Docstrings
-   PEP8
-   Không placeholder nếu có thể triển khai thật.
-   Ưu tiên chất lượng hơn tốc độ.

------------------------------------------------------------------------

# MỤC TIÊU CUỐI

Tạo một ứng dụng Windows cực kỳ đơn giản:

**Kéo ảnh → Chọn màu Fujifilm → Export**

Nếu có thư viện mã nguồn mở tốt hơn so với yêu cầu ban đầu, hãy đề xuất
trước khi triển khai thay vì tự viết lại mọi thứ.
