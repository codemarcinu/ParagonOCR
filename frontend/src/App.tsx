import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { LandingPage } from './pages/LandingPage';
import { Dashboard } from './pages/Dashboard';
import { Receipts } from './pages/Receipts';
import { Products } from './pages/Products';
import { Chat } from './pages/Chat';
import { Analytics } from './pages/Analytics';
import { ShoppingList } from './pages/ShoppingList';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/receipts" element={<Receipts />} />
        <Route path="/products" element={<Products />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/shopping-list" element={<ShoppingList />} />
      </Routes>
    </Router>
  );
}

export default App;
