import { Plus } from 'lucide-react'
import Image from 'next/image'

interface ProductCardProps {
  id: string
  name: string
  price: number
  image: string
  description: string
  onAddToCart: () => void
}

export function ProductCard({
  name,
  price,
  image,
  description,
  onAddToCart,
}: ProductCardProps) {
  return (
    <div className="border rounded-lg overflow-hidden bg-white hover:shadow-md transition-shadow">
      <div className="aspect-square bg-gray-100 overflow-hidden">
        <Image
          src={image}
          alt={name}
          width={800}
          height={800}
          className="w-full h-full object-cover"
        />
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-lg mb-1">{name}</h3>
        <p className="text-sm text-gray-600 mb-3">{description}</p>
        <div className="flex items-center justify-between">
          <span className="text-xl font-semibold">${price.toFixed(2)}</span>
          <button
            type="button"
            onClick={onAddToCart}
            className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-md hover:bg-gray-800 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add to Cart
          </button>
        </div>
      </div>
    </div>
  )
}
