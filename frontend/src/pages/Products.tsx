import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useProductStore } from '@/store/productStore';
import { Plus, Search, Edit2, TrendingUp, AlertCircle, Home } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Skeleton, Button, Input, Modal } from '@/components/ui';
import type { ProductResponse } from '@/types/api';

export function Products() {
    const {
        products,
        categories,
        loading,
        error,
        fetchProducts,
        fetchCategories,
        addProduct,
        updateProduct
    } = useProductStore();

    const [search, setSearch] = useState('');
    const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editingProduct, setEditingProduct] = useState<ProductResponse | null>(null);
    const [showPriceHistory, setShowPriceHistory] = useState<number | null>(null);

    useEffect(() => {
        fetchProducts({ search, category_id: selectedCategory || undefined });
        fetchCategories();
    }, [fetchProducts, fetchCategories, search, selectedCategory]);

    const handleEditClick = (product: ProductResponse) => {
        setEditingProduct(product);
        setIsEditModalOpen(true);
    };

    const handleAddClick = () => {
        setEditingProduct(null);
        setIsEditModalOpen(true);
    };

    const handleSaveProduct = async (e: React.FormEvent) => {
        e.preventDefault();
        const formData = new FormData(e.target as HTMLFormElement);
        const data = {
            name: formData.get('name'),
            category_id: Number(formData.get('category_id')),
            unit: formData.get('unit'),
        };

        if (editingProduct) {
            await updateProduct(editingProduct.id, data);
        } else {
            await addProduct(data);
        }
        setIsEditModalOpen(false);
    };

    // Dummy price history data for demo
    const priceHistoryData = [
        { date: '2023-01', price: 4.50 },
        { date: '2023-02', price: 4.60 },
        { date: '2023-03', price: 4.55 },
        { date: '2023-04', price: 4.80 },
        { date: '2023-05', price: 5.00 },
    ];

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
            <div className="max-w-7xl mx-auto">
                <div className="flex justify-between items-center mb-8">
                    <div className="flex items-center space-x-4">
                        <Link 
                            to="/" 
                            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                            title="Powrót do strony głównej"
                        >
                            <Home className="h-5 w-5" />
                        </Link>
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                            Baza Produktów
                        </h1>
                    </div>
                    <Button
                        onClick={handleAddClick}
                        leftIcon={<Plus className="w-5 h-5" />}
                    >
                        Dodaj Produkt
                    </Button>
                </div>

                {/* Filters */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6 flex flex-col md:flex-row gap-4">
                    <div className="relative flex-1">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none z-10">
                            <Search className="h-5 w-5 text-gray-400" />
                        </div>
                        <Input
                            type="text"
                            placeholder="Szukaj produktów..."
                            className="pl-10"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                    <div className="w-full md:w-64">
                        <div className="relative">
                            <select
                                className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white border"
                                value={selectedCategory || ''}
                                onChange={(e) => setSelectedCategory(Number(e.target.value) || null)}
                            >
                                <option value="">Wszystkie Kategorie</option>
                                {categories.map(cat => (
                                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>

                {/* Product List */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                    {loading && products.length === 0 ? (
                        <div className="p-6 space-y-4">
                            {[1, 2, 3, 4, 5].map((i) => (
                                <div key={i} className="flex items-center gap-4 p-4 border-b border-gray-200 dark:border-gray-700">
                                    <Skeleton className="h-4 w-48" variant="text" />
                                    <Skeleton className="h-4 w-32" variant="text" />
                                    <Skeleton className="h-4 w-16" variant="text" />
                                    <Skeleton className="h-4 w-16 ml-auto" variant="text" />
                                </div>
                            ))}
                        </div>
                    ) : error ? (
                        <div className="p-8 text-center text-red-500">{error}</div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                <thead className="bg-gray-50 dark:bg-gray-700">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Nazwa Produktu</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Kategoria</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Jednostka</th>
                                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Akcje</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                                    {products.length === 0 ? (
                                        <tr>
                                            <td colSpan={4} className="px-6 py-12 text-center text-gray-500">
                                                Nie znaleziono produktów spełniających kryteria.
                                            </td>
                                        </tr>
                                    ) : products.map((product) => {
                                        const category = categories.find(c => c.id === product.category_id);
                                        const isExpanded = showPriceHistory === product.id;

                                        return (
                                            <div key={product.id} style={{ display: 'contents' }}>
                                                <tr className="hover:bg-gray-50 dark:hover:bg-gray-700 group transition-colors">
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                                                        {product.name}
                                                        {Math.random() > 0.8 && (
                                                            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                                                                <AlertCircle className="w-3 h-3 mr-1" /> Dostępna alternatywa
                                                            </span>
                                                        )}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                                        {category ? (
                                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ backgroundColor: category.color ? `${category.color}20` : '#e5e7eb', color: category.color || '#374151' }}>
                                                                {category.icon} {category.name}
                                                            </span>
                                                        ) : '-'}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                                        {product.unit}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => setShowPriceHistory(isExpanded ? null : product.id)}
                                                            className="mx-2"
                                                            title="Historia Cen"
                                                        >
                                                            <TrendingUp className="w-4 h-4" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handleEditClick(product)}
                                                            title="Edytuj"
                                                        >
                                                            <Edit2 className="w-4 h-4" />
                                                        </Button>
                                                    </td>
                                                </tr>
                                                {isExpanded && (
                                                    <tr className="bg-gray-50 dark:bg-gray-800/50">
                                                        <td colSpan={4} className="px-6 py-4">
                                                            <div className="h-48 w-full max-w-lg mx-auto bg-white dark:bg-gray-800 rounded p-4 border border-gray-200 dark:border-gray-700">
                                                                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Historia Cen (Ostatnie 6 Miesięcy)</h4>
                                                                <ResponsiveContainer width="100%" height="100%">
                                                                    <AreaChart data={priceHistoryData}>
                                                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                                                        <XAxis dataKey="date" hide />
                                                                        <YAxis domain={['auto', 'auto']} hide />
                                                                        <Tooltip />
                                                                        <Area type="monotone" dataKey="price" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.1} />
                                                                    </AreaChart>
                                                                </ResponsiveContainer>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                )}
                                            </div>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            {/* Edit Modal */}
            <Modal
                isOpen={isEditModalOpen}
                onClose={() => setIsEditModalOpen(false)}
                title={editingProduct ? 'Edytuj Produkt' : 'Dodaj Nowy Produkt'}
                size="md"
            >
                <form onSubmit={handleSaveProduct}>
                    <div className="space-y-4">
                        <Input
                            name="name"
                            label="Nazwa"
                            defaultValue={editingProduct?.name}
                            required
                        />
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Kategoria</label>
                            <select
                                name="category_id"
                                defaultValue={editingProduct?.category_id || ''}
                                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white sm:text-sm px-3 py-2 border"
                            >
                                <option value="">Wybierz Kategorię</option>
                                {categories.map(cat => (
                                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                                ))}
                            </select>
                        </div>
                        <Input
                            name="unit"
                            label="Jednostka"
                            defaultValue={editingProduct?.unit || 'szt'}
                        />
                    </div>
                    <div className="mt-6 flex justify-end gap-3">
                        <Button
                            type="button"
                            variant="secondary"
                            onClick={() => setIsEditModalOpen(false)}
                        >
                            Anuluj
                        </Button>
                        <Button
                            type="submit"
                        >
                            Zapisz
                        </Button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}
