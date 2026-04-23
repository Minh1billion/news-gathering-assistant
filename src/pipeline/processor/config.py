TECH_QUERIES: list[str] = [
    "trí tuệ nhân tạo AI machine learning deep learning mô hình chatgpt openai gemini",
    "điện thoại smartphone iphone samsung chip vi xử lý màn hình camera",
    "phần mềm ứng dụng lập trình code backend frontend framework",
    "an ninh mạng bảo mật dữ liệu hacker tấn công mã hóa",
    "xe điện năng lượng pin sạc xe tự lái ô tô điện",
    "mạng xã hội facebook tiktok youtube instagram người dùng nội dung",
    "khởi nghiệp startup đầu tư gọi vốn định giá IPO",
    "máy tính laptop desktop server chip CPU GPU",
    "blockchain bitcoin ethereum tiền mã hóa crypto",
]

TOPIC_LABELS: list[str] = [
    "AI / ML",
    "Thiết bị di động",
    "Phần mềm / Dev",
    "An ninh mạng",
    "Xe điện / Năng lượng",
    "Mạng xã hội",
    "Startup / Đầu tư",
    "Phần cứng / Server",
    "Crypto / Blockchain",
]

IMPORTANT_ENGLISH_KEYWORDS: set[str] = {
    "ai", "ml", "llm", "gpt", "openai", "chatgpt", "github", "python", "java",
    "javascript", "typescript", "sql", "api", "web", "app", "ios", "android",
    "cloud", "aws", "azure", "google", "meta", "nvidia", "tesla", "apple",
    "samsung", "iphone", "bitcoin", "ethereum", "blockchain", "nft", "metaverse",
    "vr", "ar", "iot", "ota", "crm", "erp", "saas", "paas", "iaas", "edge",
    "quantum", "chip", "5g", "6g", "cpu", "gpu", "ram", "ssd", "usb",
    "wifi", "bluetooth", "hdmi", "usb-c", "oled", "amoled",
    "battery", "megapixel", "fps", "tps", "latency", "bandwidth",
    "vpn", "proxy", "firewall", "encryption", "hash", "zero-day",
    "exploit", "malware", "ransomware", "trojan", "worm", "bot", "ddos",
    "deepseek", "gemini", "claude", "copilot", "sora", "mistral", "llama",
}

STOPWORDS: set[str] = {
    "một_số", "tuy_nhiên", "đồng_thời", "không_chỉ", "thay_vì",
    "trong_khi", "bên_cạnh", "ngoài_ra", "theo_đó", "do_đó",
    "vì_vậy", "mặc_dù", "bởi_vì", "chẳng_hạn", "hay_là",
    "hơn", "sao", "tàu", "kỳ", "tận", "ưu", "tiên", "nhân", "ích",
    "gói", "bộ", "kho", "nút", "cúp", "trẻ", "già", "gia", "chủ",
    "thừa", "khuyên", "bắt", "ép", "mách", "báo", "kể", "nói",
    "có_thể", "sử_dụng", "cho_phép", "giúp_đỡ", "thực_hiện",
    "xây_dựng", "hoạt_động", "tiếp_tục", "bao_gồm", "liên_quan",
    "tham_gia", "chia_sẻ", "thành_công", "hiệu_quả", "quan_trọng",
    "trong", "của", "với", "tại", "từ", "theo", "qua", "bằng",
    "hay", "còn", "mà", "nếu", "khi", "vì", "để", "là", "và",
    "ra", "vào", "đến", "lại", "đã", "sẽ", "đang", "được", "bị",
    "một", "những", "nhiều", "này", "đây", "các", "cùng", "đó",
    "như", "sau", "trên", "cho", "cần", "có", "không", "làm",
    "người",
    "phát_triển", "khả_năng",
    "thông_tin", "nội_dung", "vấn_đề", "trường_hợp", "thời_gian",
    "việc", "điều", "cách", "loại", "số", "mức", "lần", "công_nghệ",
    "năm", "tháng", "ngày", "tuần", "giờ",
    "http", "https", "www", "com", "vn", "html", "utm", "org", "net",
    "họ", "ta", "tôi", "bạn", "chúng", "mình", "anh", "chị",
    "tp", "hcm",
    "được", "đang", "sẽ", "đã", "phải", "cần",
    "dùng", "làm", "tạo", "cho", "giúp", "trợ", "thực", "thấy",
    "hoặc", "và", "nhưng", "nếu", "vì", "nên",
    "mới", "cũ", "lớn", "nhỏ", "tốt", "xấu", "nhanh",
    "dân_trí", "vnexpress", "thanh_niên", "tuổi_trẻ", "báo_chí",
    "trang_web", "website", "công_bố", "thông_báo", "tin_tức",
    "cũng", "chưa", "ông", "vẫn", "chỉ", "trước", "khác", "thêm",
    "đạt", "đưa",
}

MOJIBAKE_PATTERNS: list[tuple[str, str]] = [
    ("latin1_as_utf8", r"Ã©|Ã |Ã¢|Æ°|Ã´|Ã³|Ã¹|Ã"),
    ("broken_sequences", r"â€™|â€œ|â€|â€˜|â€¦"),
]

WINDOW_DAYS: int = 7
MIN_CONTENT_LEN: int = 200
MIN_TOKEN_LEN: int = 20
SBERT_CONTENT_CHARS: int = 512
SBERT_BATCH_SIZE: int = 64
SEMANTIC_THRESHOLD: float = 0.25