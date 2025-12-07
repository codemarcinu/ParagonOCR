import { useEffect, useState } from 'react';
import { useReceiptStore } from '@/store/receiptStore';
import { ReceiptViewer } from '@/components/ReceiptViewer';
import { Skeleton } from '@/components/ui';

export function Receipts() {
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
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                        All Receipts
                    </h1>
                    <div className="mt-4 md:mt-0 flex space-x-2">
                        <button
                            onClick={resetFilters}
                            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                        >
                            Reset Filters
                        </button>
                    </div>
                </div>

                {/* Filters */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Date Range</label>
                        <div className="flex space-x-2">
                            <input
                                type="date"
                                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                value={filters.start_date || ''}
                                onChange={(e) => handleDateChange(e, 'start_date')}
                            />
                            <span className="text-gray-500 self-center">-</span>
                            <input
                                type="date"
                                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                value={filters.end_date || ''}
                                onChange={(e) => handleDateChange(e, 'end_date')}
                            />
                        </div>
                    </div>
                    {/* Placeholder for Shop Filter */}
                    <div className="flex items-end">
                        <span className="text-xs text-gray-500 italic">Shop filtering by ID available in backend, name search TODO.</span>
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
                        <div className="p-8 text-center text-gray-500">No receipts found.</div>
                    ) : (
                        <>
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                    <thead className="bg-gray-50 dark:bg-gray-700">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                                Date
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                                Shop
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                                Items
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                                Total
                                            </th>
                                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                                Actions
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                                        {receipts.map((receipt) => (
                                            <tr key={receipt.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                                                    {receipt.purchase_date
                                                        ? new Date(receipt.purchase_date).toLocaleDateString()
                                                        : '-'}
                                                    {receipt.purchase_time && <span className="text-gray-500 ml-2 text-xs">{receipt.purchase_time}</span>}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                                                    {receipt.shop || 'Unknown Shop'}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                                                    {receipt.items_count}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                                                    {receipt.total_amount.toFixed(2)} PLN
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <button
                                                        onClick={() => openModal(receipt.id)}
                                                        className="text-blue-600 hover:text-blue-900 dark:hover:text-blue-400"
                                                    >
                                                        View Details
                                                    </button>
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
                                            Showing <span className="font-medium">{skip + 1}</span> to <span className="font-medium">{Math.min(skip + limit, total)}</span> of <span className="font-medium">{total}</span> results
                                        </p>
                                    </div>
                                    <div>
                                        <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                                            <button
                                                onClick={() => handlePageChange(currentPage - 1)}
                                                disabled={currentPage === 1}
                                                className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-300 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-400"
                                            >
                                                Previous
                                            </button>
                                            <span className="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200">
                                                Page {currentPage} of {totalPages}
                                            </span>
                                            <button
                                                onClick={() => handlePageChange(currentPage + 1)}
                                                disabled={currentPage === totalPages}
                                                className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-300 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-400"
                                            >
                                                Next
                                            </button>
                                        </nav>
                                    </div>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Modal */}
            {modalOpen && selectedReceiptId && (
                <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
                    <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" onClick={closeModal}></div>
                        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
                        <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
                            <ReceiptViewer receiptId={selectedReceiptId} onClose={closeModal} />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
