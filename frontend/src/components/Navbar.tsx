import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  Receipt, 
  ShoppingBasket, 
  MessageSquare, 
  TrendingUp, 
  ListChecks,
  Home,
  LogOut
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { Button } from './ui';

const navigation = [
  { name: 'Strona Główna', href: '/', icon: Home },
  { name: 'Paragony', href: '/receipts', icon: Receipt },
  { name: 'Produkty', href: '/products', icon: ShoppingBasket },
  { name: 'Czat AI', href: '/chat', icon: MessageSquare },
  { name: 'Analityka', href: '/analytics', icon: TrendingUp },
  { name: 'Listy Zakupów', href: '/shopping-list', icon: ListChecks },
];

export function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, isAuthenticated } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo / Home Link */}
          <div className="flex-shrink-0">
            <Link 
              to="/" 
              className="flex items-center space-x-2 text-xl font-bold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              <Receipt className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              <span>ParagonOCR</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex md:items-center md:space-x-1 flex-1 justify-center">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`
                    flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium transition-colors
                    ${isActive
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white'
                    }
                  `}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </div>

          {/* Mobile Menu Button & Logout */}
          <div className="flex items-center space-x-2">
            {/* Mobile Menu - simplified, just show active page */}
            <div className="md:hidden">
              <select
                value={location.pathname}
                onChange={(e) => navigate(e.target.value)}
                className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                {navigation.map((item) => (
                  <option key={item.href} value={item.href}>
                    {item.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Logout Button */}
            <Button
              onClick={handleLogout}
              variant="ghost"
              size="sm"
              className="text-gray-600 hover:text-red-600 dark:text-gray-300 dark:hover:text-red-400"
              title="Wyloguj się"
            >
              <LogOut className="h-5 w-5" />
              <span className="hidden sm:inline ml-2">Wyloguj</span>
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
}

