import { Link, useLocation } from 'react-router-dom';
import { 
  Receipt, 
  ShoppingBasket, 
  MessageSquare, 
  TrendingUp, 
  ListChecks,
  Home
} from 'lucide-react';

const footerLinks = [
  { name: 'Strona Główna', href: '/', icon: Home },
  { name: 'Paragony', href: '/receipts', icon: Receipt },
  { name: 'Produkty', href: '/products', icon: ShoppingBasket },
  { name: 'Czat AI', href: '/chat', icon: MessageSquare },
  { name: 'Analityka', href: '/analytics', icon: TrendingUp },
  { name: 'Listy Zakupów', href: '/shopping-list', icon: ListChecks },
];

export function Footer() {
  const location = useLocation();

  return (
    <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {footerLinks.map((item) => {
            const isActive = location.pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`
                  flex flex-col items-center space-y-1 p-3 rounded-lg transition-colors
                  ${isActive
                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white'
                  }
                `}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className="h-5 w-5" />
                <span className="text-xs font-medium text-center">{item.name}</span>
              </Link>
            );
          })}
        </div>
        
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            © {new Date().getFullYear()} ParagonOCR. Wszystkie prawa zastrzeżone.
          </p>
        </div>
      </div>
    </footer>
  );
}

