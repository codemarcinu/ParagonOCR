import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Home, Plus, Receipt, Filter } from 'lucide-react';
import { useReceiptStore } from '@/store/receiptStore';
import { ReceiptViewer } from '@/components/ReceiptViewer';
import { FilterSidebar } from '@/components/FilterSidebar';
import { Skeleton, Button, Input, Modal, EmptyState } from '@/components/ui';

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
    const [filterSidebarOpen, setFilterSidebarOpen] = useState(false);
    const [selectedReceiptId, setSelectedReceiptId] = useState<number | null>(null);

    const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>, field: 'start_date' | 'end_date') => {
        setFilters({ [field]: e.target.value || undefined });
    };

    // In future, adding shop/category filters here would map to:
    // const handleShopChange = (id: number) => setFilters({ shop_id: id });

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
    const activeFiltersCount = Object.keys(filters).length;

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
                            onClick={() => setFilterSidebarOpen(true)}
                            variant="secondary"
                            leftIcon={<Filter className="h-4 w-4" />}
                        >
                            Filtry {activeFiltersCount > 0 && `(${activeFiltersCount})`}
                        </Button>
                        <Button
                            onClick={() => navigate('/receipts/upload')}
                            leftIcon={<Plus className="h-4 w-4" />}
                        >
                            Dodaj Paragon
                        </Button>
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
                        <EmptyState
                            icon={Receipt}
                            title="Brak paragonów"
                            description={
                                activeFiltersCount > 0
                                    ? "Nie znaleziono paragonów spełniających kryteria filtrowania."
                                    : "Twoja lista paragonów jest pusta."
                            }
                            action={
                                activeFiltersCount > 0 ? (
                                    <Button
                                        onClick={resetFilters}
                                        variant="secondary"
                                        className="mt-4"
                                    >
                                        Wyczyść Filtry
                                    </Button>
                                ) : undefined
                            }
                        />
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
                                                    {receipt.shop?.name || 'Nieznany Sklep'}
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

            {/* Filter Sidebar */}
            <FilterSidebar
                isOpen={filterSidebarOpen}
                onClose={() => setFilterSidebarOpen(false)}
                onReset={() => {
                    resetFilters();
                    setFilterSidebarOpen(false);
                }}
                onApply={() => setFilterSidebarOpen(false)}
            >
                <div className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Zakres Dat</label>
                        <div className="space-y-4">
                            <div>
                                <span className="text-xs text-gray-500 uppercase">Od</span>
                                <Input
                                    type="date"
                                    value={filters.start_date || ''}
                                    onChange={(e) => handleDateChange(e, 'start_date')}
                                    className="w-full"
                                />
                            </div>
                            <div>
                                <span className="text-xs text-gray-500 uppercase">Do</span>
                                <Input
                                    type="date"
                                    value={filters.end_date || ''}
                                    onChange={(e) => handleDateChange(e, 'end_date')}
                                    className="w-full"
                                />
                            </div>
                        </div>
                    </div>
                    {/* Placeholder for future specific filters */}
                    <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                        <p className="text-sm text-gray-400">
                            Więcej filtrów (Sklep, Kategoria) wkrótce...
                        </p>
                    </div>
                </div>
            </FilterSidebar>
        </div>
    );
}
