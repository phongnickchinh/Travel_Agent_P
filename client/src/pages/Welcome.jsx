import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, Mail, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import AuthModal from '../components/auth/AuthModal';
import { useAuth } from '../contexts/AuthContext';

export default function Welcome() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, loading } = useAuth();
  const [showContactModal, setShowContactModal] = useState(false);
  const [showAboutModal, setShowAboutModal] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, loading, navigate]);

  const currentPath = location.pathname.toLowerCase();
  const mode =
    currentPath === '/register'
      ? 'register'
      : currentPath === '/reset-password'
        ? 'reset'
        : currentPath === '/login'
          ? 'login'
          : null;

  const handleClose = () => navigate('/', { replace: true });

  // Firebase Storage background image URL
  const backgroundImageUrl = 'https://firebasestorage.googleapis.com/v0/b/travelagent-8df72.firebasestorage.app/o/view-world-monument-celebrate-world-heritage-day%20(1).jpg?alt=media&token=62a8714c-1a82-4cb9-aa46-7e9a8b0a153d';

  const [bgLoaded, setBgLoaded] = useState(false);

  const backgroundImageUrlDark = 'https://firebasestorage.googleapis.com/v0/b/travelagent-8df72.firebasestorage.app/o/vietnam-2731636.jpg?alt=media&token=b683d99b-d55b-4ccf-b760-fac6e942a0e3';

  // Preload background images
  useEffect(() => {
    const img = new Image();
    img.src = backgroundImageUrl;
    img.onload = () => setBgLoaded(true);
  }, []);

  return (
    <div className="min-h-screen h-screen relative overflow-hidden bg-brand-primary">
      {/* Background Image - Light mode */}
      <div
        className={`absolute inset-0 bg-cover bg-center bg-no-repeat dark:hidden transition-opacity duration-500 ${bgLoaded ? 'opacity-100' : 'opacity-0'}`}
        style={{ backgroundImage: `url("${backgroundImageUrl}")` }}
      />
      {/* Background Image - Dark mode */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat hidden dark:block"
        style={{ backgroundImage: `url("${backgroundImageUrlDark}")` }}
      />
      {/* Dark overlay for better text readability */}
      <div className="absolute inset-0 bg-brand-secondary/20 dark:bg-black/10" />

      {/* Content */}
      <div className="relative z-10 h-full flex flex-col">
        {/* Header */}
        <motion.header 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex items-center justify-between px-4 md:px-12 lg:px-20 py-4 md:py-6"
        >
          {/* Logo */}
          <div className="flex items-center gap-2">
            <span className="font-inter font-black text-2xl text-brand-primary dark:text-white">
              Travel Agent P
            </span>
          </div>

          {/* Nav Buttons */}
          <div className="hidden md:flex items-center gap-4">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => setShowAboutModal(true)}
              className="px-4 py-2 text-white/80 hover:text-white font-medium transition-colors"
            >
              About Us
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => setShowContactModal(true)}
              className="px-4 py-2 text-white/80 hover:text-white font-medium transition-colors"
            >
              Contact Us
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/login')}
              className="px-6 py-2.5 text-brand-primary dark:text-white dark:hover:text-white hover:text-brand-secondary font-medium rounded-full border-2 border-brand-primary/60 hover:border-brand-secondary/90 transition-colors"
            >
              Đăng nhập
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/register')}
              className="px-6 py-2.5 bg-brand-primary text-white font-medium rounded-full hover:bg-brand-secondary transition-colors shadow-lg"
            >
              Đăng ký
            </motion.button>
          </div>
        </motion.header>

        {/* Hero Section */}
        <main className="flex-1 flex flex-col items-center justify-center px-4 md:px-12 lg:px-20 text-center py-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="max-w-4xl w-full"
          >
            {/* Badge */}
            {/* <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full mb-6"
            >
              <MapPin className="w-4 h-4 text-brand-muted" />
              <span className="text-sm text-white/90 font-medium">AI-Powered Travel Planning</span>
            </motion.div> */}

            {/* Main Heading */}
            <h1 className="font-inter font-bold text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl text-white leading-tight mb-3 md:mb-4">
              WELCOME
            </h1>

            {/* Subtitle */}
            <p className="text-sm sm:text-base md:text-lg lg:text-xl text-white/90 max-w-2xl mx-auto mb-6 md:mb-8 lg:mb-10 font-dm leading-relaxed px-2">
Chào mừng đến với Travel Agent P — nhận lịch trình được cá nhân hóa bằng AI, mẹo du lịch địa phương và các ưu đãi độc quyền trực tiếp vào hộp thư đến của bạn. Mỗi gói dịch vụ bao gồm lịch trình hàng ngày được tối ưu hóa, bản đồ và ước tính chi phí.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 md:gap-4">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => navigate('/register')}
                className="group flex items-center gap-2 px-6 py-3 md:px-8 md:py-4 bg-brand-primary text-white font-poppins font-semibold rounded-full shadow-xl hover:bg-brand-secondary hover:shadow-2xl transition-all w-full sm:w-auto justify-center"
              >
                Bắt đầu ngay
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => navigate('/login')}
                className="px-6 py-3 md:px-8 md:py-4 text-white font-poppins font-medium rounded-full border-2 border-white/40 hover:border-white hover:bg-white/10 transition-all w-full sm:w-auto"
              >
                Đã có tài khoản? Đăng nhập
              </motion.button>
            </div>
          </motion.div>

          {/* Features Preview */}
          {/* <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="mt-16 md:mt-20 grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full"
          >
            {[
              { 
                icon: '🗺️', 
                title: 'Lịch trình thông minh', 
                desc: 'AI tạo lịch trình tối ưu theo sở thích' 
              },
              { 
                icon: '💰', 
                title: 'Tối ưu chi phí', 
                desc: 'Gợi ý phù hợp với ngân sách của bạn' 
              },
              { 
                icon: '📍', 
                title: 'Khám phá địa điểm', 
                desc: 'Tìm kiếm hàng ngàn điểm đến hấp dẫn' 
              },
            ].map((feature, index) => (
              <motion.div
                key={index}
                whileHover={{ y: -4, scale: 1.02 }}
                className="p-6 bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 text-center"
              >
                <span className="text-3xl mb-3 block">{feature.icon}</span>
                <h3 className="font-poppins font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-sm text-white/70 font-dm">{feature.desc}</p>
              </motion.div>
            ))}
          </motion.div> */}
        </main>

        {/* Footer */}
        <motion.footer
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.8 }}
          className="py-6 px-6 md:px-12 lg:px-20 text-center"
        >
          <p className="text-sm text-white/50 font-dm">
            © 2025 Travel Agent P | All rights reserved.
          </p>
        </motion.footer>
      </div>

      {/* Auth Modal */}
      <AuthModal open={Boolean(mode)} mode={mode || 'login'} onClose={handleClose} />

      {/* About Us Modal */}
      <AnimatePresence>
        {showAboutModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowAboutModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              onClick={(e) => e.stopPropagation()}
              className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-white dark:bg-gray-900 rounded-2xl shadow-2xl"
            >
              {/* Header */}
              <div className="relative px-6 py-5 bg-brand-primary dark:bg-brand-dark">
                <div className="flex items-center">
                  <h2 className="font-poppins font-bold text-xl text-white">About Us</h2>
                </div>
                <button
                  onClick={() => setShowAboutModal(false)}
                  className="absolute top-4 right-4 p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-full transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Content */}
              <div className="p-6 space-y-4">
                <div className="text-center space-y-1">
                  <h3 className="font-poppins font-bold text-lg text-gray-900 dark:text-white">Travel Agent P</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">AI-Powered Travel Planning</p>
                </div>

                <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                  Chúng tôi là nền tảng lập kế hoạch du lịch thông minh, sử dụng công nghệ AI tiên tiến để tạo ra những lịch trình du lịch được cá nhân hóa hoàn hảo cho bạn.
                </p>

                <div className="space-y-3 pt-2 text-center">
                  <div className="space-y-1">
                    <h4 className="font-medium text-gray-900 dark:text-white">Sứ mệnh</h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Giúp mọi người khám phá thế giới một cách thông minh và tiết kiệm.</p>
                  </div>
                  <div className="space-y-1">
                    <h4 className="font-medium text-gray-900 dark:text-white">Công nghệ</h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Sử dụng LLM và Machine Learning để tối ưu hóa lịch trình.</p>
                  </div>
                  <div className="space-y-1">
                    <h4 className="font-medium text-gray-900 dark:text-white">Phạm vi</h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Hỗ trợ hàng nghìn điểm đến trên toàn thế giới.</p>
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800 border-t border-gray-100 dark:border-gray-700">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setShowAboutModal(false)}
                  className="w-full py-3 bg-brand-primary hover:bg-brand-secondary text-white font-medium rounded-xl transition"
                >
                  Đóng
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Contact Us Modal */}
      <AnimatePresence>
        {showContactModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowContactModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              onClick={(e) => e.stopPropagation()}
              className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-white dark:bg-gray-900 rounded-2xl shadow-2xl"
            >
              {/* Header */}
              <div className="relative px-6 py-5 bg-brand-primary dark:bg-brand-dark">
                <div className="flex items-center gap-3">
                  <Mail className="w-6 h-6 text-white" />
                  <h2 className="font-poppins font-bold text-xl text-white">Contact Us</h2>
                </div>
                <button
                  onClick={() => setShowContactModal(false)}
                  className="absolute top-4 right-4 p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-full transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Content */}
              <div className="p-6 space-y-5">
                <p className="text-gray-600 dark:text-gray-300">
                  Chúng tôi luôn sẵn sàng hỗ trợ bạn. Hãy liên hệ với chúng tôi qua các kênh sau:
                </p>

                <div className="space-y-4">
                  {/* Email */}
                  <a
                    href="mailto:support@travelagentp.com"
                    className="p-4 min-h-24 bg-gray-50 dark:bg-gray-800 rounded-xl hover:bg-brand-muted/30 dark:hover:bg-brand-dark/30 transition group overflow-hidden flex flex-col items-center justify-center text-center"
                  >
                    <h4 className="font-medium text-gray-900 dark:text-white group-hover:text-brand-primary transition">Email</h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">support@travelagentp.com</p>
                  </a>

                  {/* Phone */}
                  <a
                    href="tel:+84123456789"
                    className="p-4 min-h-24 bg-gray-50 dark:bg-gray-800 rounded-xl hover:bg-brand-muted/30 dark:hover:bg-brand-dark/30 transition group overflow-hidden flex flex-col items-center justify-center text-center"
                  >
                    <h4 className="font-medium text-gray-900 dark:text-white group-hover:text-brand-primary transition">Hotline</h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">+84 123 456 789</p>
                  </a>

                  {/* Address */}
                  <div className="p-4 min-h-24 bg-gray-50 dark:bg-gray-800 rounded-xl overflow-hidden flex flex-col items-center justify-center text-center">
                    <h4 className="font-medium text-gray-900 dark:text-white">Địa chỉ</h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Hà Nội, Việt Nam</p>
                  </div>
                </div>

                {/* Working hours */}
                <div className="p-4 bg-brand-muted/30 dark:bg-brand-dark/20 rounded-xl">
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">Giờ làm việc</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Thứ 2 - Thứ 6: 8:00 - 18:00<br />
                    Thứ 7 - Chủ nhật: 9:00 - 17:00
                  </p>
                </div>
              </div>

              {/* Footer */}
              <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800 border-t border-gray-100 dark:border-gray-700">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setShowContactModal(false)}
                  className="w-full py-3 bg-brand-primary hover:bg-brand-secondary text-white font-medium rounded-xl transition"
                >
                  Đóng
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
