import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Assessment from './pages/Assessment';
import Results from './pages/Results';

/**
 * KIRA — Main Application Component
 *
 * Sets up React Router with three main routes:
 *   / — Home (landing page)
 *   /assess — Assessment (image upload + GPS input)
 *   /results/:sessionId — Results (assessment display)
 *
 * Owner: Frontend Lead
 */
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/assess" element={<Assessment />} />
        <Route path="/results/:sessionId" element={<Results />} />
      </Routes>
    </Router>
  );
}

export default App;
