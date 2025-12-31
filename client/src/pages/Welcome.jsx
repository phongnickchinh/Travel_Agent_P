import { motion } from 'framer-motion';
import { ArrowRight, Compass, MapPin } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import AuthModal from '../components/auth/AuthModal';

export default function Welcome() {
  const location = useLocation();
  const navigate = useNavigate();

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

  const backgroundImageUrlDark = 'https://firebasestorage.googleapis.com/v0/b/travelagent-8df72.firebasestorage.app/o/vietnam-2731636.jpg?alt=media&token=b683d99b-d55b-4ccf-b760-fac6e942a0e3';

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background Image */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: `url(${backgroundImageUrl})` }}
      >
        <img src={backgroundImageUrl} alt="" className="dark:hidden" />
        <img src={backgroundImageUrlDark} alt="" className="hidden dark:block" />
        {/* Dark overlay for better text readability */}
        <div className="absolute inset-0 bg-brand-secondary/20 dark:bg-black/10" />
      </div>

      {/* Content */}
      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Header */}
        <motion.header 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex items-center justify-between px-6 md:px-12 lg:px-20 py-6"
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
        <main className="flex-1 flex flex-col items-center justify-center px-6 md:px-12 lg:px-20 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="max-w-4xl"
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
            <h1 className="font-inter font-bold text-15xl md:text-6xl lg:text-15xl text-white leading-tight mb-4">
              WELCOME
            </h1>

            {/* Subtitle */}
            <p className="text-lg md:text-xl text-white max-w-2xl mx-auto mb-10 font-dm leading-relaxed">
Chào mừng đến với Travel Agent P — nhận lịch trình được cá nhân hóa bằng AI, mẹo du lịch địa phương và các ưu đãi độc quyền trực tiếp vào hộp thư đến của bạn. Mỗi gói dịch vụ bao gồm lịch trình hàng ngày được tối ưu hóa, bản đồ và ước tính chi phí.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => navigate('/register')}
                className="group flex items-center gap-2 px-8 py-4 bg-brand-primary text-white font-poppins font-semibold rounded-full shadow-xl hover:bg-brand-secondary hover:shadow-2xl transition-all"
              >
                Bắt đầu ngay
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => navigate('/login')}
                className="px-8 py-4 text-white font-poppins font-medium rounded-full border-2 border-white/40 hover:border-white hover:bg-white/10 transition-all"
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

        {/* Mobile Nav Buttons */}
        <div className="md:hidden fixed bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent">
          <div className="flex gap-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/login')}
              className="flex-1 py-3 text-white font-medium rounded-full border-2 border-white/40"
            >
              Đăng nhập
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/register')}
              className="flex-1 py-3 bg-brand-primary text-white font-medium rounded-full"
            >
              Đăng ký
            </motion.button>
          </div>
        </div>
      </div>

      {/* Auth Modal */}
      <AuthModal open={Boolean(mode)} mode={mode || 'login'} onClose={handleClose} />
    </div>
  );
}
