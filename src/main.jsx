import React from 'react';
import { createRoot } from 'react-dom/client';
import InteractiveBackground from './components/InteractiveBackground.jsx';
import Lanyard from './components/Lanyard.jsx';
import './react-lanyard.css';

function App() {
  return (
    <div className="react-lanyard-stage" aria-label="Interactive student ID lanyard">
      <Lanyard
        position={[0, 0, 10]}
        gravity={[0, -40, 0]}
        frontImage={`${import.meta.env.BASE_URL}portfolio-assets/card-front-blank.svg?v=2`}
        backImage={`${import.meta.env.BASE_URL}portfolio-assets/card-back-blank.svg?v=1`}
        imageFit="contain"
        lanyardWidth={0.65}
      />
    </div>
  );
}

createRoot(document.getElementById('background-root')).render(<InteractiveBackground />);
createRoot(document.getElementById('lanyard-root')).render(<App />);



