/**
 * Receipt Viewer Component for displaying and editing receipt details.
 */

import { useEffect, useState } from 'react';
import { getReceipt, updateReceipt } from '@/lib/api';
import type { ReceiptDetailsResponse } from '@/types/api';
import { Button, Input } from './ui';
import { Pencil, Save, X } from 'lucide-react';

interface ReceiptViewerProps {
  receiptId: number;
  onClose?: () => void;
}

export function ReceiptViewer({ receiptId, onClose }: ReceiptViewerProps) {
  const [receipt, setReceipt] = useState<ReceiptDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedReceipt, setEditedReceipt] = useState<ReceiptDetailsResponse | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchReceipt = async () => {
      try {
        setLoading(true);
        const data = await getReceipt(receiptId);
        setReceipt(data);
        setEditedReceipt(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Nie udało się załadować paragonu');
      } finally {
        setLoading(false);
      }
    };

    fetchReceipt();
  }, [receiptId]);

  const handleSave = async () => {
    if (!editedReceipt) return;
    setSaving(true);
    try {
      // Prepare data for update (simplified for now)
      // In a real scenario, we'd only send changed fields or specific DTO
      await updateReceipt(receiptId, editedReceipt);
      setReceipt(editedReceipt);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Błąd zapisu');
    } finally {
      setSaving(false);
    }
  };

  const cancelEdit = () => {
    setEditedReceipt(receipt);
    setIsEditing(false);
  };

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

  if (!receipt || !editedReceipt) {
    return null;
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-h-[90vh] overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          {isEditing ? 'Edycja Paragonu' : 'Szczegóły Paragonu'}
        </h2>
        <div className="flex space-x-2">
          {!isEditing ? (
            <Button onClick={() => setIsEditing(true)} variant="secondary" size="sm" leftIcon={<Pencil className="w-4 h-4" />}>
              Edytuj
            </Button>
          ) : (
            <>
              <Button onClick={cancelEdit} variant="ghost" size="sm" disabled={saving}>
                Anuluj
              </Button>
              <Button onClick={handleSave} size="sm" disabled={saving} leftIcon={<Save className="w-4 h-4" />}>
                {saving ? 'Zapisywanie...' : 'Zapisz'}
              </Button>
            </>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 ml-2"
            >
              <X className="h-6 w-6" />
            </button>
          )}
        </div>
      </div>

      {/* Receipt Info */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Sklep</p>
          {isEditing ? (
            <Input
              value={editedReceipt.shop.name || ''}
              onChange={(e) => setEditedReceipt({
                ...editedReceipt,
                shop: { ...editedReceipt.shop, name: e.target.value }
              })}
            />
          ) : (
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {receipt.shop?.name || 'Nieznany'}
            </p>
          )}
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Data</p>
          {isEditing ? (
            <Input
              type="date"
              value={editedReceipt.purchase_date || ''}
              onChange={(e) => setEditedReceipt({ ...editedReceipt, purchase_date: e.target.value })}
            />
          ) : (
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {receipt.purchase_date
                ? new Date(receipt.purchase_date).toLocaleDateString('pl-PL')
                : '-'}
              {receipt.purchase_time && ` ${receipt.purchase_time}`}
            </p>
          )}
        </div>
      </div>

      {/* Items Table */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Pozycje ({receipt.items.length})
        </h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase w-1/2">
                  Produkt
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Ilość
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Cena (PLN)
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Suma
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {(isEditing ? editedReceipt.items : receipt.items).map((item, index) => (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-4 py-2 text-sm text-gray-900 dark:text-gray-100">
                    {isEditing ? (
                      <div className="space-y-1">
                        <Input
                          value={item.product?.name || item.raw_name}
                          onChange={(e) => {
                            const newItems = [...editedReceipt.items];
                            newItems[index] = { ...item, product: { ...item.product, name: e.target.value } };
                            setEditedReceipt({ ...editedReceipt, items: newItems });
                          }}
                          className="h-8 text-sm"
                          placeholder="Nazwa produktu"
                        />
                      </div>
                    ) : (
                      <div>
                        <p className="font-medium">
                          {item.product.name || item.raw_name}
                        </p>
                        {item.product.name && item.raw_name !== item.product.name && (
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            Oryginalna nazwa: {item.raw_name}
                          </p>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-900 dark:text-gray-100">
                    {isEditing ? (
                      <Input
                        type="number"
                        value={item.quantity}
                        onChange={(e) => {
                          const newItems = [...editedReceipt.items];
                          newItems[index] = { ...item, quantity: Number(e.target.value) };
                          // Auto-recalc total
                          newItems[index].total_price = newItems[index].quantity * (newItems[index].unit_price || 0);
                          setEditedReceipt({ ...editedReceipt, items: newItems });
                        }}
                        className="h-8 w-20 text-sm"
                      />
                    ) : (
                      `${item.quantity} ${item.unit || 'szt'}`
                    )}
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-900 dark:text-gray-100">
                    {isEditing ? (
                      <Input
                        type="number"
                        step="0.01"
                        value={item.unit_price || 0}
                        onChange={(e) => {
                          const newItems = [...editedReceipt.items];
                          newItems[index] = { ...item, unit_price: Number(e.target.value) };
                          // Auto-recalc total
                          newItems[index].total_price = newItems[index].quantity * (newItems[index].unit_price || 0);
                          setEditedReceipt({ ...editedReceipt, items: newItems });
                        }}
                        className="h-8 w-24 text-sm"
                      />
                    ) : (
                      item.unit_price ? item.unit_price.toFixed(2) : '-'
                    )}
                  </td>
                  <td className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-gray-100">
                    {item.total_price.toFixed(2)}
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
            <div className="flex justify-between text-lg font-bold border-t border-gray-200 dark:border-gray-700 pt-2">
              <span className="text-gray-900 dark:text-white">Razem:</span>
              <span className="text-gray-900 dark:text-white">
                {/* Dynamically calc total during edit */}
                {(isEditing
                  ? editedReceipt.items.reduce((acc, item) => acc + item.total_price, 0)
                  : receipt.total_amount
                ).toFixed(2)} PLN
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

