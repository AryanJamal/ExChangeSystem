import { useState, useEffect } from 'react';
import { api } from '../services/apiService';
import { Plus, X, Coins,CheckCircle, DollarSign, Wallet, Edit, Trash2, Check, ArrowUp, ArrowDown, Clock, XCircle } from 'lucide-react';
import formatDate from '../components/formatdate';

const CryptoTransactions = () => {
    const [transactions, setTransactions] = useState([]);
    // eslint-disable-next-line no-unused-vars
    const [partners, setPartners] = useState([]);
    const [safes, setSafes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [currentId, setCurrentId] = useState(null);

    // We've replaced window.confirm with a state-driven modal concept.
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [transactionToDelete, setTransactionToDelete] = useState(null);


    const [formData, setFormData] = useState({
        transaction_type: 'Buy',
        partner: '',
        usdt_amount: '',
        usdt_price: '',
        crypto_safe: '',
        bonus: '',
        bonus_currency: 'USDT',
        status: 'Pending',
        payment_safe: '',
        currency: 'USDT',
        client_name: ''
    });


    
    // Fetch initial data
    useEffect(() => {
        const fetchData = async () => {
            try {
                const [transRes, partnersRes, safesRes] = await Promise.all([
                    api.cryptoTransactions.getAll(),
                    api.safePartnersApi.getAll(),
                    api.safeTypes.getAll()
                ]);

                setTransactions(transRes.data);
                setPartners(partnersRes.data);
                setSafes(safesRes.data);
                setLoading(false);
            } catch (err) {
                setError(err.message);
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (isEditing) {
                const updatedTransaction = await api.cryptoTransactions.update(currentId, formData);
                setTransactions(transactions.map(t =>
                    t.id === currentId ? updatedTransaction.data : t
                ));
            } else {
                const res = await api.cryptoTransactions.create(formData);
                setTransactions([...transactions, res.data]);
            }
            resetForm();
        } catch (err) {
            setError(err.message);
        }
    };

    const handleEdit = (transaction) => {
        setFormData({
            transaction_type: transaction.transaction_type,
            partner: transaction.partner?.id || '',
            usdt_amount: transaction.usdt_amount,
            usdt_price: transaction.usdt_price,
            crypto_safe: transaction.crypto_safe?.id || '',
            bonus: transaction.bonus,
            bonus_currency: transaction.bonus_currency,
            status: transaction.status,
            payment_safe: transaction.payment_safe?.id || '',
            currency: transaction.currency,
            client_name: transaction.client_name || ''
        });
        setIsEditing(true);
        setCurrentId(transaction.id);
        setShowForm(true);
    };

    const handleDelete = (id) => {
        setTransactionToDelete(id);
        setShowDeleteModal(true);
    };
    

    const confirmDelete = async () => {
        try {
            await api.cryptoTransactions.delete(transactionToDelete);
            setTransactions(transactions.filter(t => t.id !== transactionToDelete));
            setShowDeleteModal(false);
            setTransactionToDelete(null);
        } catch (err) {
            setError(err.message);
        }
    };


    const resetForm = () => {
        setFormData({
            transaction_type: 'Buy',
            partner: '',
            usdt_amount: '',
            usdt_price: '',
            crypto_safe: '',
            bonus: '',
            bonus_currency: 'USDT',
            status: 'Pending',
            payment_safe: '',
            currency: 'USDT',
            client_name: ''
        });
        setIsEditing(false);
        setCurrentId(null);
        setShowForm(false);
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'Completed': return <CheckCircle size={16} className="text-green-400" />;
            case 'Cancelled': return <XCircle size={16} className="text-red-400" />;
            default: return <Clock size={16} className="text-amber-400" />;
        }
    };

    if (loading) return (
        <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
    );

    if (error) return (
        <div className="p-4 min-h-screen text-white">
            <div className="mx-auto max-w-7xl">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <h1 className="text-2xl font-bold">کڕین و فرۆشتنی کریپتۆ</h1>
                </div>
                <div className="bg-white/10 backdrop-blur-lg border border-white/20 rounded-xl shadow-lg p-4 sm:p-6 md:p-0 overflow-hidden">
                    <div className="gap-3 p-4 text-left text-red-700">
                        Error: {error}
                    </div>
                </div>
            </div>
        </div>
    );

    return (
        <div className="p-4 min-h-screen bg-slate-50-900 ml-0 sm:mt-6 md:mt-0 xsm:mt-6">
            <div className="mx-auto">
                <div className="flex justify-between items-center mb-6">
                    <h1 className="text-2xl font-bold text-white">کڕین و فرۆشتنی کریپتۆ</h1>
                    <button
                        onClick={() => setShowForm(!showForm)}
                        className="flex items-center gap-2 bg-white/10 hover:bg-white/20 backdrop-blur-sm border border-white/20 text-white px-4 py-2 rounded-lg transition-all"
                    >
                        <Plus size={18} />
                        {showForm ? "لابردن" : "مامەڵە"}
                    </button>
                </div>

                {/* Form Panel */}
                {showForm && (
                    <div className="bg-gray-800/80 backdrop-blur-lg border border-white/20 rounded-xl shadow-lg p-6 mb-8 transition-all">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-semibold text-white">
                                {isEditing ? "Edit Transaction" : "Create New Transaction"}
                            </h2>
                            <button onClick={resetForm} className="text-white/70 hover:text-white">
                                <X size={20} />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Transaction Type */}
                            <div>
                            <label className="block text-white/80 mb-2">جۆری مامەڵە</label>
                            <div className="flex border border-white/20">
                                <button
                                    type="button"
                                    onClick={() => handleInputChange({ target: { name: "transaction_type", value: "Buy" } })}
                                    className={`w-full text-center py-2 rounded-md transition-all ${
                                        formData.transaction_type === "Buy"
                                            ? "bg-blue-600 text-white"
                                            : "text-white/70 hover:bg-white/10"
                                    }`}
                                >
                                    کڕین
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleInputChange({ target: { name: "transaction_type", value: "Sell" } })}
                                    className={`w-full text-center py-2 rounded-md transition-all ${
                                        formData.transaction_type === "Sell"
                                            ? "bg-blue-600 text-white"
                                            : "text-white/70 hover:bg-white/10"
                                    }`}
                                >
                                    فرۆشتن
                                </button>
                            </div>
                        </div>

                            {/* Status */}
                            <div>
                            <label className="block text-white/80 mb-2">بارودۆخ</label>
                            <div className="flex border border-white/20">
                                <button
                                    type="button"
                                    onClick={() => handleInputChange({ target: { name: "status", value: "Pending" } })}
                                    className={`w-full text-center py-2 rounded-md transition-all ${
                                        formData.status === "Pending"
                                            ? "bg-blue-600 text-white"
                                            : "text-white/70 hover:bg-white/10"
                                    }`}
                                >
                                    قەرز
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleInputChange({ target: { name: "status", value: "Completed" } })}
                                    className={`w-full text-center py-2 rounded-md transition-all ${
                                        formData.status === "Completed"
                                            ? "bg-blue-600 text-white"
                                            : "text-white/70 hover:bg-white/10"
                                    }`}
                                >
                                    واصڵ
                                </button>
                            </div>
                        </div>

                            {/* USDT Amount */}
                            <div>
                                <label className="block text-white/80 mb-2">بڕی USDT</label>
                                <input
                                    type="number"
                                    name="usdt_amount"
                                    value={formData.usdt_amount}
                                    onChange={handleInputChange}
                                    className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                    required
                                    step="0.01"
                                    min="0"
                                />
                            </div>

                            {/* USDT Price */}
                            <div>
                                <label className="block text-white/80 mb-2">نرخی USDT</label>
                                <input
                                    type="number"
                                    name="usdt_price"
                                    value={formData.usdt_price}
                                    onChange={handleInputChange}
                                    className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                    required
                                    step="0.01"
                                    min="0"
                                />
                            </div>

                            {/* Crypto Safe */}
                            <div>
                                <label className="block text-white/80 mb-2">شوێنی کریپتۆ</label>
                                <select
                                    name="crypto_safe"
                                    value={formData.crypto_safe}
                                    onChange={handleInputChange}
                                    className="w-full bg-slate-800/80 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                    required
                                >
                                    <option value="">شوێنی کریپتۆ دیاری بکە..</option>
                                    {safes
            .filter(safe => safe.type === 'Crypto')
            .map(safe => (
                <option key={safe.id} value={safe.id}>{safe.name}</option>
            ))}
                                </select>
                            </div>

                            {/* Payment Safe */}
                            <div>
                                <label className="block text-white/80 mb-2">شوێنی پارە</label>
                                <select
                                    name="payment_safe"
                                    value={formData.payment_safe}
                                    onChange={handleInputChange}
                                    className="w-full bg-slate-800/80 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                    required
                                >
                                    <option value="">شوێنی پارە دیاری بکە..</option>
                                    {safes
            .filter(safe => safe.type === 'Physical')
            .map(safe => (
                <option key={safe.id} value={safe.id}>{safe.name}</option>
            ))}
                                </select>
                            </div>

                            {/* Bonus */}
                            <div>
                                <label className="block text-white/80 mb-2">بڕی عمولە</label>
                                
                                <input
                                    type="number"
                                    name="bonus"
                                    value={formData.bonus}
                                    onChange={handleInputChange}
                                    className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                    step="0.01"
                                    min="0"
                                />
                            </div>

                            {/* Bonus Currency */}
                            <div>
                            <label className="block text-white/80 mb-2">دراوی عمولە</label>
                            <div className="flex border border-white/20">
                                <button
                                    type="button"
                                    onClick={() => handleInputChange({ target: { name: "bonus_currency", value: "USDT" } })}
                                    className={`flex-1 flex items-center justify-center gap-1 py-2 rounded-md transition-all ${
                                        formData.bonus_currency === "USDT"
                                            ? "bg-blue-600 text-white"
                                            : "text-white/70 hover:bg-white/10"
                                    }`}
                                >
                                    <Coins size={18} /> USDT
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleInputChange({ target: { name: "bonus_currency", value: "USD" } })}
                                    className={`flex-1 flex items-center justify-center gap-1 py-2 rounded-md transition-all ${
                                        formData.bonus_currency === "USD"
                                            ? "bg-blue-600 text-white"
                                            : "text-white/70 hover:bg-white/10"
                                    }`}
                                >
                                    <DollarSign size={18}/> USD
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleInputChange({ target: { name: "bonus_currency", value: "IQD" } })}
                                    className={`flex-1 flex items-center justify-center gap-1 py-2 rounded-md transition-all ${
                                        formData.bonus_currency === "IQD"
                                            ? "bg-blue-600 text-white"
                                            : "text-white/70 hover:bg-white/10"
                                    }`}
                                >
                                    <Wallet size={18} /> IQD
                                </button>
                            </div>
                        </div>

                            {/* Currency */}
                            <div>
                            <label className="block text-white/80 mb-2">دراوی فرۆشتن/کڕین</label>
                            <div className="flex border border-white/20">
                                <button
                                    type="button"
                                    onClick={() => handleInputChange({ target: { name: "currency", value: "USDT" } })}
                                    className={`flex-1 flex items-center justify-center gap-1 py-2 rounded-md transition-all ${
                                        formData.currency === "USDT"
                                            ? "bg-blue-600 text-white"
                                            : "text-white/70 hover:bg-white/10"
                                    }`}
                                >
                                    <Coins size={18} /> USDT
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleInputChange({ target: { name: "currency", value: "USD" } })}
                                    className={`flex-1 flex items-center justify-center gap-1 py-2 rounded-md transition-all ${
                                        formData.currency === "USD"
                                            ? "bg-blue-600 text-white"
                                            : "text-white/70 hover:bg-white/10"
                                    }`}
                                >
                                    <DollarSign size={18} /> USD
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleInputChange({ target: { name: "currency", value: "IQD" } })}
                                    className={`flex-1 flex items-center justify-center gap-1 py-2 rounded-md transition-all ${
                                        formData.currency === "IQD"
                                            ? "bg-blue-600 text-white"
                                            : "text-white/70 hover:bg-white/10"
                                    }`}
                                >
                                    <Wallet size={18} /> IQD
                                </button>
                            </div>
                        </div>

                        {/* Client Name */}
                            <div>
                                <label className="block text-white/80 mb-2">ناوی فرۆشیار/کڕیار</label>
                                <input
                                    type="text"
                                    name="client_name"
                                    value={formData.client_name}
                                    onChange={handleInputChange}
                                    className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                />
                            </div>

                            {/* Form Actions */}
                            <div className="md:col-span-2 flex gap-3 pt-2">
                                <button
                                    type="submit"
                                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-all"
                                >
                                    <CheckCircle size={18} />
                                    {isEditing ? "Update" : "Create"}
                                </button>

                                <button
                                    type="button"
                                    onClick={resetForm}
                                    className="flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/20 text-white px-4 py-2 rounded-lg transition-all"
                                >
                                    <X size={18} />
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                )}

                {/* Transactions Cards */}
                <div className="bg-white/10 backdrop-blur-lg border border-white/20 rounded-xl shadow-lg p-4 sm:p-6 md:p-0 overflow-hidden">
                    {transactions.length === 0 ? (
                        <div className="p-6 text-center text-white/60 bg-white/10 backdrop-blur-lg border border-white/20 rounded-xl shadow-lg md:col-span-2 lg:col-span-3">
                            No transactions found
                        </div>
                    ) : (
                        <>
                            <div className="grid grid-cols-1 lg:grid-cols-4 md:grid-cols-2 gap-3 p-4">
                                {transactions.map((transaction) => (
                                    <div key={transaction.id} className="bg-gray-800/80 backdrop-blur-lg border border-white/20 rounded-xl shadow-lg p-6 flex flex-col justify-between">
                                        {/* Top section: Type and Status */}
                                        <div className="flex items-center justify-between mb-4 pb-4 border-b border-white/10">
                                            <div className="flex items-center gap-2">
                                                {transaction.transaction_type === 'Buy' ? (
                                                    <ArrowUp className="text-green-400" size={20} />
                                                ) : (
                                                    <ArrowDown className="text-red-400" size={20} />
                                                )}
                                                <span className="text-lg font-semibold text-white">{transaction.transaction_type === 'Buy' ? 'کڕین' : 'فرۆشتن'}</span>
                                            </div>
                                            <div className="flex items-center gap-2 px-3 py-1 rounded-full text-white/90 text-sm"
                                                style={{
                                                    backgroundColor: transaction.status === 'Completed' ? 'rgba(52, 211, 153, 0.2)' :
                                                        transaction.status === 'Cancelled' ? 'rgba(239, 68, 68, 0.2)' :
                                                            'rgba(251, 191, 36, 0.2)'
                                                }}>
                                                {getStatusIcon(transaction.status)}
                                                <span>{transaction.status === 'Completed' ? 'واصڵ' : 'قەرز'}</span>
                                            </div>
                                        </div>

                                        {/* Main details */}
                                        <div className="space-y-3 flex-grow">
                                            <div className="flex justify-between items-center">
                                                <span className="text-white/80 text-sm">شەریک:</span>
                                                <span className="font-medium text-white">{transaction.partner?.partner.name || 'نییە'}</span>
                                            </div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-white/80 text-sm ">USDT:</span>
                                                <span className="font-medium text-white">{Number(transaction.usdt_amount).toLocaleString('en-US')} USDT</span>
                                            </div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-white/80 text-sm">نرخی کڕین:</span>
                                                <span className="font-medium text-white">{Number(transaction.usdt_price).toLocaleString()} {transaction.currency}</span>
                                            </div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-white/80 text-sm">ناو:</span>
                                                <span className="font-medium text-white">{transaction.client_name || 'نەزانراو'}</span>
                                            </div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-white/80 text-sm">کات:</span>
                                                <span className="font-medium text-white">{formatDate(transaction.created_at)}</span>
                                            </div>
                                        </div>

                                        {/* Actions */}
                                        <div className="flex justify-end gap-3 pt-4 border-t border-white/10 mt-4">
                                            <button
                                                onClick={() => handleEdit(transaction)}
                                                className="text-white/70 hover:text-blue-400 transition-colors p-2 rounded-full hover:bg-white/5"
                                                title="Edit"
                                            >
                                                <Edit size={18} />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(transaction.id)}
                                                className="text-white/70 hover:text-red-400 transition-colors p-2 rounded-full hover:bg-white/5"
                                                title="Delete"
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            </div>
            {/* Delete Confirmation Modal */}
            {showDeleteModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
                    <div className="bg-white/10 backdrop-blur-lg border border-white/20 rounded-xl shadow-lg p-6 w-full max-w-sm">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-semibold text-white">Confirm Delete</h2>
                            <button onClick={() => setShowDeleteModal(false)} className="text-white/70 hover:text-white">
                                <X size={20} />
                            </button>
                        </div>
                        <p className="text-white/80 mb-6">Are you sure you want to delete this transaction? This action cannot be undone.</p>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={confirmDelete}
                                className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-all"
                            >
                                <Trash2 size={18} />
                                Delete
                            </button>
                            <button
                                onClick={() => setShowDeleteModal(false)}
                                className="flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/20 text-white px-4 py-2 rounded-lg transition-all"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CryptoTransactions;
