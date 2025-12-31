import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';

import TailwindTest from './pages/TailwindTest';
import CreatePlan from './pages/user/CreatePlan';
import CreatePlanNew from './pages/user/CreatePlanNew';
import Dashboard from './pages/user/Dashboard';
import PlanDetail from './pages/user/PlanDetail';
import Trash from './pages/user/Trash';
import Welcome from './pages/Welcome';

// Search Autocomplete Demo Pages (Week 3 Deliverable)
import SearchDemo from './components/SearchDemo';
import SearchExamples from './pages/SearchExamples';

import './App.css';


import ThemeToggle from './components/ui/ThemeToggle';
import ProtectedRoute from './contexts/ProtectedRoute';

function App() {
  return (
    <Router>
      <Routes>
        {/* Guest/public routes rendered via welcome page + modal popups */}
        <Route path="/" element={<Welcome />} />
        <Route path="/login" element={<Welcome />} />
        <Route path="/register" element={<Welcome />} />
        <Route path="/reset-password" element={<Welcome />} />
        <Route path="/tailwind-test" element={<TailwindTest />} />
        <Route path="/shared/:shareToken" element={<PlanDetail />} />

        {/* Dashboard routes */}
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/dashboard/create-plan" element={<ProtectedRoute><CreatePlanNew /></ProtectedRoute>} />
        <Route path="/dashboard/plan/:planId" element={<ProtectedRoute><PlanDetail /></ProtectedRoute>} />
        <Route path="/dashboard/trash" element={<ProtectedRoute><Trash /></ProtectedRoute>} />

        {/* Legacy routes */}
        <Route path="/dashboard/:username" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/create-plan" element={<ProtectedRoute><CreatePlan /></ProtectedRoute>} />
        <Route path="/search-demo" element={<ProtectedRoute><SearchDemo /></ProtectedRoute>} />
        <Route path="/search-examples" element={<ProtectedRoute><SearchExamples /></ProtectedRoute>} />

        {/* Thêm các route yêu cầu auth khác ở đây */}
      </Routes>
      <ThemeToggle />
    </Router>
  );
}
export default App;
