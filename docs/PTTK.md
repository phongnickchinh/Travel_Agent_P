1. Mô tả bài toán 
    - Ứng dụng sủ dụng AI agent để lập kế hoạch du lịch cá nhân hóa dựa trên sở thích và ngân sách của người dùng.
    - Tích hợp các API bên ngoài như Google Places, TripAdvisor để lấy thông tin về địa điểm, đánh giá.
    - Đầu vào là thông tin: Điểm đến, thời gian, ngân sách, sở thích.
    - Đầu ra là kế hoạch du lịch chi tiết bao gồm các địa điểm tham quan, hoạt động, lịch trình.
2. Yêu cầu chức năng
    - Khách:
        + Đăng ký/đăng nhập tài khoản.
        + Chức năng xây tour: Nhập thông tin du lịch: điểm đến, thời gian, ngân sách, sở thích. Xem kế hoạch du lịch được AI đề xuất.
            + Xem chi tiết lịch trình, địa điểm, hoạt động.
            + Xem đánh giá, hình ảnh của các địa điểm.
            + Xem ước tính chi phí.
        + Lưu kế hoạch dưới dạng PDF, excel, gửi email.
    - Người dùng đăng nhập:
        + Quản lý hồ sơ cá nhân.
            + Quản lí xác thực
            + Quản lí thông tin cá nhân
        + Chức năng xây tour: Mở rộng: 
            + Lựa chọn nhập thông tin mới hoặc sử dụng lịch sử.
            + Lịch trình rút gọn
            + Lịch trình tiết kiệm
            + Tự điều chỉnh lịch trình cho phù hợp với sở thích.
            + Xem lịch sử kế hoạch đã tạo.
        + Dữ liệu được lưu trữ để cải thiện đề xuất trong tương lai.
    - Quản trị viên:
        + Quản lý người dùng, kế hoạch.
        + Xem thống kê sử dụng ứng dụng.
        + Quản lý API bên ngoài, giám sát hiệu suất hệ thống.
