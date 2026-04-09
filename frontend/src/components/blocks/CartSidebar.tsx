import { ShoppingCart, Trash2 } from 'lucide-react'

interface CartItem {
  id: string
  name: string
  price: number
  quantity: number
}

interface CartSidebarProps {
  items: CartItem[]
  onRemoveItem: (id: string) => void
  onCheckout: () => void
}

export function CartSidebar({
  items,
  onRemoveItem,
  onCheckout,
}: CartSidebarProps) {
  const total = items.reduce((sum, item) => sum + item.price * item.quantity, 0)
  const itemCount = items.reduce((sum, item) => sum + item.quantity, 0)

  return (
    <div className="w-96 border-l bg-white flex flex-col h-screen sticky top-0">
      <div className="p-6 border-b">
        <div className="flex items-center gap-2 mb-1">
          <ShoppingCart className="w-5 h-5" />
          <h2 className="text-xl font-semibold">Cart</h2>
        </div>
        <p className="text-sm text-gray-600">
          {itemCount} {itemCount === 1 ? 'item' : 'items'}
        </p>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {items.length === 0 ? (
          <div className="text-center py-12">
            <ShoppingCart className="w-12 h-12 mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500">Your cart is empty</p>
          </div>
        ) : (
          <div className="space-y-4">
            {items.map((item) => (
              <div key={item.id} className="flex gap-3 pb-4 border-b">
                <div className="flex-1">
                  <h3 className="font-medium mb-1">{item.name}</h3>
                  <p className="text-sm text-gray-600">Qty: {item.quantity}</p>
                  <p className="font-semibold mt-2">
                    ${(item.price * item.quantity).toFixed(2)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onRemoveItem(item.id)}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                  aria-label="Remove item"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="p-6 border-t space-y-4">
        <div className="flex items-center justify-between text-lg">
          <span className="font-medium">Total</span>
          <span className="font-semibold">${total.toFixed(2)}</span>
        </div>
        <button
          type="button"
          onClick={onCheckout}
          disabled={items.length === 0}
          className="w-full py-3 bg-black text-white rounded-md font-medium hover:bg-gray-800 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          Proceed to Payment
        </button>
      </div>
    </div>
  )
}
