'use client'

import { useState } from 'react'
import { CartSidebar } from '@/components/blocks/CartSidebar'
import { ErrorBanner } from '@/components/blocks/ErrorBanner'
import { ProductCard } from '@/components/blocks/ProductCard'

interface CartItem {
  id: string
  name: string
  price: number
  quantity: number
}

const PRODUCTS = [
  {
    id: '1',
    name: 'Wireless Headphones',
    price: 299.99,
    description: 'Premium noise-canceling headphones with 30-hour battery life',
    image:
      'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&q=80',
  },
  {
    id: '2',
    name: 'Smart Watch',
    price: 399.99,
    description:
      'Fitness tracking, heart rate monitor, and smartphone notifications',
    image:
      'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80',
  },
  {
    id: '3',
    name: 'Wireless Keyboard',
    price: 79.99,
    description: 'Ergonomic aluminum keyboard for better feeling and typing',
    image:
      'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&q=80',
  },
]

type ErrorType = 'payment' | 'restricted-item'

const RESTRICTED_PRODUCTS = ['3']

export default function HomePage() {
  const [cart, setCart] = useState<CartItem[]>([])
  const [errorType, setErrorType] = useState<ErrorType | null>(null)

  const addToCart = (productId: string) => {
    const product = PRODUCTS.find((p) => p.id === productId)
    if (!product) return

    // Check if product is restricted
    if (RESTRICTED_PRODUCTS.includes(productId)) {
      setErrorType('restricted-item')
      return
    }

    setCart((prevCart) => {
      const existingItem = prevCart.find((item) => item.id === productId)
      if (existingItem) {
        return prevCart.map((item) =>
          item.id === productId
            ? { ...item, quantity: item.quantity + 1 }
            : item,
        )
      }
      return [
        ...prevCart,
        {
          id: product.id,
          name: product.name,
          price: product.price,
          quantity: 1,
        },
      ]
    })
  }

  const removeFromCart = (productId: string) => {
    setCart((prevCart) => prevCart.filter((item) => item.id !== productId))
  }

  const handleCheckout = () => {
    setErrorType('payment')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex">
        <div className="flex-1">
          <div className="max-w-6xl mx-auto p-6">
            {errorType && (
              <div className="mb-6">
                <ErrorBanner
                  errorType={errorType}
                  onDismiss={() => setErrorType(null)}
                />
              </div>
            )}

            <div className="mb-8">
              <h1 className="text-3xl font-semibold mb-2">Tech Store</h1>
              <p className="text-gray-600">
                Premium tech accessories for your workspace
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {PRODUCTS.map((product) => (
                <ProductCard
                  key={product.id}
                  {...product}
                  onAddToCart={() => addToCart(product.id)}
                />
              ))}
            </div>
          </div>
        </div>

        <CartSidebar
          items={cart}
          onRemoveItem={removeFromCart}
          onCheckout={handleCheckout}
        />
      </div>
    </div>
  )
}
