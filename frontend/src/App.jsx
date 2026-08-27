import React, { useState } from 'react';
import { Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom';
import Navbar from './components/organisms/Navbar';
import LandingScreen from './components/templates/LandingScreen';
import SignupScreen from './components/templates/SignupScreen';
import LoginScreen from './components/templates/LoginScreen';
import AddChildScreen from './components/templates/AddChildScreen';
import ParentDashboardScreen from './components/templates/ParentDashboardScreen';
import StudentDashboardScreen from './components/templates/StudentDashboardScreen';
import LessonPlayerScreen from './components/templates/LessonPlayerScreen';
import QuizScreen from './components/templates/QuizScreen';
import EvidenceSubmitScreen from './components/templates/EvidenceSubmitScreen';
import LessonCompleteScreen from './components/templates/LessonCompleteScreen';
import PortfolioScreen from './components/templates/PortfolioScreen';
import AdminDashboardScreen from './components/templates/AdminDashboardScreen';
import { useAuth } from './hooks/useAuth';
import { authAPI, parentAPI } from './services/api';

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUser, login, register, logout } = useAuth();
  const [activeChild, setActiveChild] = useState(() => {
    try {
      const saved = localStorage.getItem('activeChild');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return null;
  });

  const saveActiveChild = (child) => {
    setActiveChild(child);
    if (child) {
      localStorage.setItem('activeChild', JSON.stringify(child));
    } else {
      localStorage.removeItem('activeChild');
    }
  };

  const [activeLessonId, setActiveLessonId] = useState(1);
  const [currentLessonData, setCurrentLessonData] = useState(null);
  const [quizResultData, setQuizResultData] = useState(null);
  const [activeDayNumber, setActiveDayNumber] = useState(1);
  const [activeActivityType, setActiveActivityType] = useState('Explore');

  const selectLessonContext = (lessonRef) => {
    const id = typeof lessonRef === 'object' ? lessonRef?.id : lessonRef;
    setActiveLessonId(id || 1);
    setActiveDayNumber(typeof lessonRef === 'object' ? (lessonRef?.day_number || 1) : 1);
    setActiveActivityType(typeof lessonRef === 'object' ? (lessonRef?.activity_type || 'Explore') : 'Explore');
  };

  const go = (path) => { navigate(path.startsWith('/') ? path : `/${path}`); window.scrollTo(0, 0); };

  const handleLogin = async (email, pw) => {
    const user = await login(email, pw);
    if (user.role === 'student') {
      saveActiveChild({ id: user.child_id, name: user.name, avatar: user.avatar, profile_image_url: user.profile_image_url });
      go('/student');
    } else {
      saveActiveChild(null);
      go(user.role === 'admin' ? '/admin' : '/parent');
    }
  };

  const handleSignup = async (name, email, pw) => {
    await register(name, email, pw);
    go('/add-child');
  };

  const handleAddChild = async (childData) => {
    try {
      let pId = currentUser?.id;
      if (!pId) {
        try {
          const u = JSON.parse(localStorage.getItem('currentUser') || '{}');
          pId = u?.id;
        } catch (e) {}
      }
      const res = await authAPI.addChild({
        ...childData,
        parent_id: pId,
      });
      if (res?.data) {
        let created = res.data;
        if (childData.profile_image) {
          const upload = await parentAPI.uploadProfileImage(created.id, childData.profile_image);
          created = { ...created, profile_image_url: upload.data.profile_image_url };
        }
        saveActiveChild(created);
      }
    } catch (e) {
      console.error('Failed to add child:', e);
      throw e;
    }
    go('/parent');
  };

  const handleLogout = () => { logout(); saveActiveChild(null); go('/'); };

  const userRole = currentUser?.role || 'parent';
  const currentPath = location.pathname.replace('/', '') || 'landing';
  const publicPages = ['', 'landing', 'signup', 'login'];
  const isProtected = !publicPages.includes(currentPath);
  if (isProtected && !currentUser && currentPath !== 'add-child') {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="app">
      <Navbar currentScreen={currentPath} userRole={userRole} onNavigate={go} activeChild={activeChild} currentUser={currentUser} onLogout={handleLogout} />
      <Routes>
        <Route path="/" element={<LandingScreen onNavigate={go} onStartLesson={() => go('/login')} />} />
        <Route path="/signup" element={<SignupScreen onNavigate={go} onSignup={handleSignup} />} />
        <Route path="/login" element={<LoginScreen onNavigate={go} onLogin={handleLogin} />} />
        <Route path="/add-child" element={currentUser?.role === 'parent' ? <AddChildScreen parentName={currentUser?.name} onNavigate={go} onAddChild={handleAddChild} /> : <Navigate to={currentUser?.role === 'student' ? '/student' : '/login'} replace />} />
        <Route path="/parent" element={currentUser?.role === 'parent' ? <ParentDashboardScreen parentId={currentUser?.id} onSelectChild={(c) => { saveActiveChild(c); go('/student'); }} onAddChild={() => go('/add-child')} onViewPortfolio={() => go('/portfolio')} /> : <Navigate to={currentUser?.role === 'student' ? '/student' : currentUser?.role === 'admin' ? '/admin' : '/login'} replace />} />
        <Route path="/student" element={activeChild ? <StudentDashboardScreen child={activeChild} onBackToParent={currentUser?.role === 'parent' ? () => go('/parent') : null} onStartLesson={(lessonRef) => { selectLessonContext(lessonRef); go('/lesson'); }} onStartQuiz={(lessonRef) => { selectLessonContext(lessonRef); go('/quiz'); }} onViewPortfolio={() => go('/portfolio')} /> : <Navigate to={currentUser?.role === 'student' ? '/login' : '/parent'} replace />} />
        <Route path="/lesson" element={<LessonPlayerScreen lessonId={activeLessonId} dayNumber={activeDayNumber} activityType={activeActivityType} child={activeChild} onExit={() => go('/student')} onProceedToQuiz={(l) => { setCurrentLessonData(l); setActiveLessonId(l?.id || activeLessonId); go('/quiz'); }} />} />
        <Route path="/quiz" element={<QuizScreen lesson={currentLessonData} lessonId={activeLessonId} dayNumber={activeDayNumber} child={activeChild} onExit={() => go('/student')} onQuizComplete={(res) => { setQuizResultData(res); go('/submit'); }} />} />
        <Route path="/submit" element={<EvidenceSubmitScreen lesson={currentLessonData} lessonId={activeLessonId} dayNumber={activeDayNumber} child={activeChild} quizResult={quizResultData} onExit={() => go('/student')} onSubmitSuccess={() => go('/complete')} />} />
        <Route path="/complete" element={<LessonCompleteScreen child={activeChild} quizResult={quizResultData} onViewPortfolio={() => go('/portfolio')} onNextLesson={() => go('/student')} />} />
        <Route path="/portfolio" element={<PortfolioScreen child={activeChild} onBack={() => go(currentUser?.role === 'student' ? '/student' : '/parent')} />} />
        <Route path="/admin/*" element={currentUser?.role === 'admin' ? <AdminDashboardScreen onExit={handleLogout} /> : <Navigate to={currentUser ? '/parent' : '/login'} replace />} />
      </Routes>
    </div>
  );
}
