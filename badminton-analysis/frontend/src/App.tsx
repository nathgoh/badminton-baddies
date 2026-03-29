import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import UploadPage from './pages/UploadPage';
import SelectPage from './pages/SelectPage';
import ResultsPage from './pages/ResultsPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/select/:videoId" element={<SelectPage />} />
        <Route path="/results/:videoId" element={<ResultsPage />} />
      </Routes>
    </Router>
  );
}

export default App;
