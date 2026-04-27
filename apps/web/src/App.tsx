import { Routes, Route, Navigate } from 'react-router-dom'
import { LessonLibrary } from './components/LessonLibrary'
import { LessonDetail } from './components/LessonDetail'
import { ReviewDashboard } from './components/ReviewDashboard'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LessonLibrary />} />
      <Route path="/review" element={<ReviewDashboard />} />
      <Route path="/lessons/:lessonId" element={<LessonDetail />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
