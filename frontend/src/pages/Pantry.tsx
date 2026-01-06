import { useEffect, useState } from 'react';
import { fetchPantryItems, consumeItem, wasteItem } from '../lib/api';
import type { PantryItemResponse } from '../types/api';
import { LoadingSpinner, Card, Button } from '../components/ui';
import { Trash2, Check, AlertTriangle, PackageOpen } from 'lucide-react';
import { parseISO, differenceInDays } from 'date-fns';
import toast from 'react-hot-toast';

export const Pantry = () => {
    const [items, setItems] = useState<PantryItemResponse[]>([]);
    const [loading, setLoading] = useState(true);

    const loadData = async () => {
        try {
            const data = await fetchPantryItems();
            // Sortowanie: najpierw te, które zaraz się przeterminują
            const sorted = data.sort((a, b) => {
                if (!a.expiration_date) return 1;
                if (!b.expiration_date) return -1;
                return new Date(a.expiration_date).getTime() - new Date(b.expiration_date).getTime();
            });
            setItems(sorted);
        } catch (error) {
            console.error(error);
            toast.error('Nie udało się pobrać zawartości spiżarni');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleConsume = async (id: number, name: string) => {
        try {
            await consumeItem(id);
            toast.success(`Zjedzono: ${name}`);
            loadData(); // Odśwież listę
        } catch {
            toast.error('Błąd aktualizacji');
        }
    };

    const handleWaste = async (id: number, name: string) => {
        if (!confirm(`Czy na pewno wyrzucasz ${name}?`)) return;
        try {
            await wasteItem(id);
            toast.error(`Wyrzucono: ${name}`); // Czerwony toast dla marnowania
            loadData();
        } catch {
            toast.error('Błąd aktualizacji');
        }
    };

    const getExpirationStatus = (dateStr: string | null) => {
        if (!dateStr) return { color: 'text-gray-500', label: 'Brak daty', bg: 'bg-gray-100', days: null, borderColor: 'border-gray-200' };

        const days = differenceInDays(parseISO(dateStr), new Date());

        if (days < 0) return { color: 'text-red-600 font-bold', label: `Przeterminowane ${Math.abs(days)} dni!`, bg: 'bg-red-100', days, borderColor: 'border-red-500' };
        if (days <= 2) return { color: 'text-orange-600 font-bold', label: `Ważne jeszcze ${days} dni`, bg: 'bg-orange-100', days, borderColor: 'border-orange-500' };
        if (days <= 7) return { color: 'text-yellow-600', label: `Ważne ${days} dni`, bg: 'bg-yellow-50', days, borderColor: 'border-yellow-500' };

        return { color: 'text-green-600', label: `Ważne ${days} dni`, bg: 'bg-green-50', days, borderColor: 'border-green-500' };
    };

    if (loading) return <div className="flex justify-center p-10"><LoadingSpinner /></div>;

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <PackageOpen className="text-blue-600" /> Moja Spiżarnia
                </h1>
                <div className="text-sm text-gray-500">
                    Liczba produktów: {items.length}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {items.map((item) => {
                    const status = getExpirationStatus(item.expiration_date);

                    return (
                        <Card key={item.id} className={`flex flex-col justify-between ${status.bg} dark:bg-gray-800 border-l-4 ${status.borderColor}`}>
                            <div className="p-4">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h3 className="font-semibold text-lg text-gray-900 dark:text-white">
                                            {item.product.normalized_name}
                                        </h3>
                                        <p className="text-sm text-gray-500">
                                            Ilość: {item.quantity} {item.unit || item.product.unit}
                                        </p>
                                    </div>
                                    {status.days !== null && status.days < 0 && (
                                        <AlertTriangle className="text-red-500 w-5 h-5" />
                                    )}
                                </div>

                                <div className={`mt-2 text-sm ${status.color}`}>
                                    {status.label} <br />
                                    <span className="text-xs text-gray-400">({item.expiration_date})</span>
                                </div>
                            </div>

                            <div className="bg-white/50 dark:bg-gray-700/50 p-3 flex justify-end space-x-2 rounded-b-lg">
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    className="text-red-600 hover:bg-red-50 border border-red-200"
                                    onClick={() => handleWaste(item.id, item.product.normalized_name)}
                                    title="Wyrzuć (Zmarnowane)"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </Button>
                                <Button
                                    size="sm"
                                    className="bg-green-600 hover:bg-green-700 text-white"
                                    onClick={() => handleConsume(item.id, item.product.normalized_name)}
                                    title="Oznacz jako zjedzone"
                                >
                                    <Check className="w-4 h-4 mr-1" /> Zjedzone
                                </Button>
                            </div>
                        </Card>
                    );
                })}
            </div>

            {items.length === 0 && (
                <div className="text-center py-10 text-gray-500">
                    Twoja lodówka jest pusta! Zeskanuj paragon, aby ją zapełnić.
                </div>
            )}
        </div>
    );
};

export default Pantry;
