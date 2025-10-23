import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';

import DashboardWelcome from './pages/user/Dashboard';
import DashboardLayout from './pages/user/DashboardLayout';
import Login from './pages/user/Login';
import Register from './pages/user/Register';
import ResetPassword from './pages/user/ResetPassword';

import './App.css';


import ProtectedRoute from './contexts/ProtectedRoute';

function App() {
  return (
    <Router>
      <Routes>
        {/* Guest/public routes */}
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* Authenticated routes */}
        <Route path="/dashboard/:username" element={<ProtectedRoute><DashboardWelcome /></ProtectedRoute>} />
        {/* <Route path="/user/:username" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>} /> */}

        {/* Thêm các route yêu cầu auth khác ở đây */}
      </Routes>
    </Router>
  );
}
export default App;
