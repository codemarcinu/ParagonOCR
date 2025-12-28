/**
 * Dashboard page showing recent receipts and spending summary.
 */

import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Home, Receipt } from 'lucide-react';
import { useReceiptStore } from '@/store/receiptStore';
import { ReceiptUploader } from '@/components/ReceiptUploader';
import { Skeleton, EmptyState } from '@/components/ui';

export function Dashboard() {
  const { receipts, loading, error, fetchReceipts } = useReceiptStore();

  useEffect(() => {
    fetchReceipts({ limit: 10 });
  }, [fetchReceipts]);

  // Calculate spending summary
  const totalSpending = receipts.reduce((sum, r) => sum + r.total_amount, 0);
  const avgReceipt = receipts.length > 0 ? totalSpending / receipts.length : 0;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center space-x-4 mb-8">
          <Link
            to="/"
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
            title="Powrót do strony głównej"
          >
            <Home className="h-5 w-5" />
          </Link>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Panel ParagonOCR
          </h1>
        </div>

        {/* Upload Section */}
        <div className="mb-8">
          <ReceiptUploader />
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Wszystkie Paragony
            </h3>
            <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
              {receipts.length}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Wydatki (30 dni)
            </h3>
            <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
              {totalSpending.toFixed(2)} PLN
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Średni Paragon
            </h3>
            <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
              {avgReceipt.toFixed(2)} PLN
            </p>
          </div>
        </div>

        {/* Recent Receipts */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Ostatnie Paragony
            </h2>
          </div>
          <div className="p-6">
            {loading && (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-4 p-4 border-b border-gray-200 dark:border-gray-700">
                    <Skeleton className="h-4 w-24" variant="text" />
                    <Skeleton className="h-4 w-32" variant="text" />
                    <Skeleton className="h-4 w-16" variant="text" />
                    <Skeleton className="h-4 w-20" variant="text" />
                  </div>
                ))}
              </div>
            )}

            {error && (
              <div className="text-center py-8">
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            {!loading && !error && receipts.length === 0 && (
              <EmptyState
                icon={Receipt}
                title="Brak paragonów"
                description="Nie dodałeś jeszcze żadnych paragonów. Prześlij pierwszy, aby zobaczyć statystyki!"
                action={
                  <div className="mt-4">
                    {/* The uploader is already prominent above, so maybe just a pointer or scroll? 
                        For now, let's keep it simple or maybe scroll to top? 
                        The uploader IS above, so no action needed, or maybe focus input? 
                        Let's just leave action empty or point up.
                    */}
                  </div>
                }
              />
            )}

            {!loading && !error && receipts.length > 0 && (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Data
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Sklep
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Pozycje
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Suma
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {receipts.map((receipt) => (
                      <tr key={receipt.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                          {receipt.purchase_date
                            ? new Date(receipt.purchase_date).toLocaleDateString('pl-PL')
                            : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                          {receipt.shop?.name || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                          {receipt.items_count}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                          {receipt.total_amount.toFixed(2)} PLN
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

