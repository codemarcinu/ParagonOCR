import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Home, Plus } from 'lucide-react';
import { useReceiptStore } from '@/store/receiptStore';
import { ReceiptViewer } from '@/components/ReceiptViewer';
import { Skeleton, Button, Input, Modal } from '@/components/ui';

export function Receipts() {
    const navigate = useNavigate();
    const {
        receipts,
        loading,
        error,
        total,
        limit,
        skip,
        filters,
        fetchReceipts,
        setFilters,
        setPage,
        resetFilters
    } = useReceiptStore();

    useEffect(() => {
        fetchReceipts();
    }, [fetchReceipts]);

    const handlePageChange = (newPage: number) => {
        setPage(newPage);
    };

    const [modalOpen, setModalOpen] = useState(false);
    const [selectedReceiptId, setSelectedReceiptId] = useState<number | null>(null);

    const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>, field: 'start_date' | 'end_date') => {
        setFilters({ [field]: e.target.value || undefined });
    };

    const openModal = (id: number) => {
        setSelectedReceiptId(id);
        setModalOpen(true);
    };

    const closeModal = () => {
        setModalOpen(false);
        setSelectedReceiptId(null);
    };

    const currentPage = Math.floor(skip / limit) + 1;
    const totalPages = Math.ceil(total / limit);

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8 relative">
            <div className="max-w-7xl mx-auto">
                <div className="flex flex-col md:flex-row md:items-center justify-between mb-8">
                    <div className="flex items-center space-x-4">
                        <Link 
                            to="/" 
                            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                            title="Powrót do strony głównej"
                        >
                            <Home className="h-5 w-5" />
                        </Link>
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                            Wszystkie Paragony
                        </h1>
                    </div>
                    <div className="mt-4 md:mt-0 flex space-x-2">
                        <Button
                            onClick={() => navigate('/receipts/upload')}
                            leftIcon={<Plus className="h-4 w-4" />}
                        >
                            Dodaj Paragon
                        </Button>
                        <Button
                            onClick={resetFilters}
                            variant="secondary"
                        >
                            Resetuj Filtry
                        </Button>
                    </div>
                </div>

                {/* Filters */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Zakres Dat</label>
                        <div className="flex space-x-2">
                            <Input
                                type="date"
                                value={filters.start_date || ''}
                                onChange={(e) => handleDateChange(e, 'start_date')}
                                className="flex-1"
                            />
                            <span className="text-gray-500 self-center">-</span>
                            <Input
                                type="date"
                                value={filters.end_date || ''}
                                onChange={(e) => handleDateChange(e, 'end_date')}
                                className="flex-1"
                            />
                        </div>
                    </div>
                    {/* Placeholder for Shop Filter */}
                    <div className="flex items-end">
                        <span className="text-xs text-gray-500 italic">Filtrowanie sklepów po ID dostępne w backendzie, wyszukiwanie po nazwie TODO.</span>
                    </div>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                    {loading && receipts.length === 0 ? (
                        <div className="p-6 space-y-4">
                            {[1, 2, 3, 4, 5].map((i) => (
                                <div key={i} className="flex items-center gap-4 p-4 border-b border-gray-200 dark:border-gray-700">
                                    <Skeleton className="h-4 w-24" variant="text" />
                                    <Skeleton className="h-4 w-32" variant="text" />
                                    <Skeleton className="h-4 w-16" variant="text" />
                                    <Skeleton className="h-4 w-20" variant="text" />
                                    <Skeleton className="h-4 w-24 ml-auto" variant="text" />
                                </div>
                            ))}
                        </div>
                    ) : error ? (
                        <div className="p-8 text-center text-red-500">{error}</div>
                    ) : receipts.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">Nie znaleziono paragonów.</div>
                    ) : (
                        <>
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
                                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                                Akcje
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
                                                    {receipt.purchase_time && <span className="text-gray-500 ml-2 text-xs">{receipt.purchase_time}</span>}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                                                    {receipt.shop || 'Nieznany Sklep'}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                                                    {receipt.items_count}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                                                    {receipt.total_amount.toFixed(2)} PLN
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => openModal(receipt.id)}
                                                    >
                                                        Zobacz Szczegóły
                                                    </Button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {/* Pagination */}
                            <div className="bg-white dark:bg-gray-800 px-4 py-3 flex items-center justify-between border-t border-gray-200 dark:border-gray-700 sm:px-6">
                                <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                                    <div>
                                        <p className="text-sm text-gray-700 dark:text-gray-300">
                                            Wyświetlanie <span className="font-medium">{skip + 1}</span> do <span className="font-medium">{Math.min(skip + limit, total)}</span> z <span className="font-medium">{total}</span> wyników
                                        </p>
                                    </div>
                                    <div>
                                        <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Paginacja">
                                            <Button
                                                onClick={() => handlePageChange(currentPage - 1)}
                                                disabled={currentPage === 1}
                                                variant="secondary"
                                                size="sm"
                                                className="rounded-l-md"
                                            >
                                                Poprzednia
                                            </Button>
                                            <span className="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200">
                                                Strona {currentPage} z {totalPages}
                                            </span>
                                            <Button
                                                onClick={() => handlePageChange(currentPage + 1)}
                                                disabled={currentPage === totalPages}
                                                variant="secondary"
                                                size="sm"
                                                className="rounded-r-md"
                                            >
                                                Następna
                                            </Button>
                                        </nav>
                                    </div>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Modal */}
            <Modal
                isOpen={modalOpen && selectedReceiptId !== null}
                onClose={closeModal}
                size="xl"
            >
                {selectedReceiptId && <ReceiptViewer receiptId={selectedReceiptId} onClose={closeModal} />}
            </Modal>
        </div>
    );
}
