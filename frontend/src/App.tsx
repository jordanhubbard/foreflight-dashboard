import { Routes, Route } from 'react-router-dom'
import { Box } from '@mui/material'
import UploadPage from './pages/UploadPage'

function App() {
  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <Routes>
        {/* Single route - upload page that leads to dashboard */}
        <Route path="/" element={<UploadPage />} />
        <Route path="*" element={<UploadPage />} />
      </Routes>
    </Box>
  )
}

export default App
