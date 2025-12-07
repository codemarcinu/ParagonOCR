import React from 'react';
import {
    ScanLine,
    LayoutDashboard,
    ShoppingBasket,
    MessageSquare,
    Database,
    Receipt,
    ArrowRight,
    TrendingUp,
    Clock
} from 'lucide-react';
import { Link } from 'react-router-dom';

export function LandingPage() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 text-gray-900 dark:text-gray-100 font-sans">

            {/* Hero Section */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16">
                <div className="text-center">
                    <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400">
                        ParagonOCR <span className="text-gray-400 font-light text-3xl align-top">Web</span>
                    </h1>
                    <p className="mt-4 max-w-2xl mx-auto text-xl text-gray-500 dark:text-gray-300">
                        Twój osobisty asystent finansowy i zarządca domowego magazynu.
                    </p>

                    <div className="mt-8 flex justify-center gap-4">
                        <Link to="/receipts" className="group">
                            <button className="flex items-center px-8 py-3 border border-transparent text-base font-medium rounded-full text-white bg-blue-600 hover:bg-blue-700 md:py-4 md:text-lg shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-1">
                                <ScanLine className="mr-2 h-6 w-6 group-hover:animate-pulse" />
                                Skanuj Paragon
                            </button>
                        </Link>
                        <Link to="/chat">
                            <button className="flex items-center px-8 py-3 border border-gray-300 dark:border-gray-600 text-base font-medium rounded-full text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 md:py-4 md:text-lg shadow hover:shadow-md transition-all">
                                <MessageSquare className="mr-2 h-6 w-6" />
                                Zapytaj AI
                            </button>
                        </Link>
                    </div>
                </div>
            </div>

            {/* Stats Overview (Mock Data for Looks) */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-16">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Wydatki (Ten miesiąc)</p>
                            <p className="text-3xl font-bold mt-1">2 450.00 PLN</p>
                        </div>
                        <div className="p-3 bg-red-100 dark:bg-red-900/30 rounded-full">
                            <TrendingUp className="h-6 w-6 text-red-600 dark:text-red-400" />
                        </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Ostatni Paragon</p>
                            <p className="text-xl font-bold mt-1 truncate max-w-[150px]">Lidl - Zakupy</p>
                            <p className="text-xs text-gray-400">Dzisiaj, 14:30</p>
                        </div>
                        <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-full">
                            <Clock className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                        </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Produkty w Bazie</p>
                            <p className="text-3xl font-bold mt-1">1,248</p>
                        </div>
                        <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-full">
                            <Database className="h-6 w-6 text-green-600 dark:text-green-400" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Feature Grid */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
                <h2 className="text-2xl font-bold mb-8 text-gray-800 dark:text-gray-100">Główne Moduły</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">

                    <FeatureCard
                        to="/dashboard"
                        icon={<LayoutDashboard className="h-8 w-8 text-purple-600" />}
                        title="Dashboard"
                        description="Pełny przegląd Twoich finansów i statystyk zakupowych."
                        color="hover:border-purple-500"
                    />

                    <FeatureCard
                        to="/receipts"
                        icon={<Receipt className="h-8 w-8 text-blue-600" />}
                        title="Moje Paragony"
                        description="Przeglądaj, wyszukuj i zarządzaj zeskanowanymi paragonami."
                        color="hover:border-blue-500"
                    />

                    <FeatureCard
                        to="/products"
                        icon={<ShoppingBasket className="h-8 w-8 text-green-600" />}
                        title="Baza Produktów"
                        description="Katalog wszystkich kupionych produktów z historią cen."
                        color="hover:border-green-500"
                    />

                    <FeatureCard
                        to="/chat"
                        icon={<MessageSquare className="h-8 w-8 text-indigo-600" />}
                        title="Asystent AI"
                        description="Rozmawiaj z Bielikiem o swoich zakupach, przepisach i diecie."
                        color="hover:border-indigo-500"
                    />

                    <FeatureCard
                        to="/analytics"
                        icon={<TrendingUp className="h-8 w-8 text-red-600" />}
                        title="Analityka"
                        description="Szczegółowe wykresy i trendy wydatków."
                        color="hover:border-red-500"
                    />

                </div>
            </div>

        </div>
    );
}

function FeatureCard({ to, icon, title, description, color }: { to: string, icon: React.ReactNode, title: string, description: string, color: string }) {
    return (
        <Link to={to} className={`group bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 ${color} border-l-4`}>
            <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-xl group-hover:scale-110 transition-transform">
                    {icon}
                </div>
                <ArrowRight className="h-5 w-5 text-gray-300 group-hover:text-gray-600 dark:group-hover:text-gray-400 transition-colors" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">{title}</h3>
            <p className="text-gray-500 dark:text-gray-400 leading-relaxed">
                {description}
            </p>
        </Link>
    )
}
