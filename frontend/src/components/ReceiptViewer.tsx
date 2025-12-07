/**
 * Receipt Viewer Component for displaying and editing receipt details.
 */

import { useEffect, useState } from 'react';
import { getReceipt } from '@/lib/api';

interface ReceiptViewerProps {
  receiptId: number;
  onClose?: () => void;
}

interface ReceiptDetails {
  id: number;
  shop: {
    id: number | null;
    name: string | null;
    location: string | null;
  };
  purchase_date: string | null;
  purchase_time: string | null;
  total_amount: number;
  subtotal: number | null;
  tax: number | null;
  items: Array<{
    id: number;
    product: {
      id: number | null;
      name: string | null;
    };
    raw_name: string;
    quantity: number;
    unit: string | null;
    unit_price: number | null;
    total_price: number;
    discount: number | null;
  }>;
  source_file: string;
  created_at: string | null;
}

export function ReceiptViewer({ receiptId, onClose }: ReceiptViewerProps) {
  const [receipt, setReceipt] = useState<ReceiptDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReceipt = async () => {
      try {
        setLoading(true);
        const data = await getReceipt(receiptId);
        setReceipt(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load receipt');
      } finally {
        setLoading(false);
      }
    };

    fetchReceipt();
  }, [receiptId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!receipt) {
    return null;
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Receipt Details
        </h2>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Receipt Info */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Shop</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {receipt.shop.name || 'Unknown'}
          </p>
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Date</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {receipt.purchase_date
              ? new Date(receipt.purchase_date).toLocaleDateString()
              : '-'}
            {receipt.purchase_time && ` ${receipt.purchase_time}`}
          </p>
        </div>
      </div>

      {/* Items Table */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Items ({receipt.items.length})
        </h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Product
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Quantity
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Unit Price
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Total
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {receipt.items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                    <div>
                      <p className="font-medium">
                        {item.product.name || item.raw_name}
                      </p>
                      {item.product.name && item.raw_name !== item.product.name && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          Raw: {item.raw_name}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                    {item.quantity} {item.unit || 'szt'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                    {item.unit_price ? `${item.unit_price.toFixed(2)} PLN` : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">
                    {item.total_price.toFixed(2)} PLN
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Totals */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <div className="flex justify-end">
          <div className="w-64 space-y-2">
            {receipt.subtotal !== null && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Subtotal:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {receipt.subtotal.toFixed(2)} PLN
                </span>
              </div>
            )}
            {receipt.tax !== null && receipt.tax > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Tax:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {receipt.tax.toFixed(2)} PLN
                </span>
              </div>
            )}
            <div className="flex justify-between text-lg font-bold border-t border-gray-200 dark:border-gray-700 pt-2">
              <span className="text-gray-900 dark:text-white">Total:</span>
              <span className="text-gray-900 dark:text-white">
                {receipt.total_amount.toFixed(2)} PLN
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

