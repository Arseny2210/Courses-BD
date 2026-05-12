"use client";

import { formatPrice } from "@/lib/api";
import { Product } from "@/lib/types";

type ProductCardProps = {
  product: Product;
  onAddToCart: (productId: string) => void;
  busy: boolean;
};

export function ProductCard({ product, onAddToCart, busy }: ProductCardProps) {
  return (
    <article className="product-card">
      <div className="product-image-wrap">
        {product.image_url ? (
          <img src={product.image_url} alt={product.name} className="product-image" />
        ) : (
          <div className="product-image fallback">Нет изображения</div>
        )}
      </div>

      <div className="product-content">
        <div className="product-meta">
          <span className={product.stock > 0 ? "stock-badge success" : "stock-badge danger"}>
            {product.stock > 0 ? `В наличии: ${product.stock}` : "Нет на складе"}
          </span>
          <span className="price-tag">{formatPrice(product.price)}</span>
        </div>

        <h3>{product.name}</h3>
        <p>{product.description}</p>

        <button
          className="primary-button stretch"
          disabled={busy || product.stock === 0}
          onClick={() => onAddToCart(product.id)}
        >
          {busy ? "Добавляем..." : "Добавить в корзину"}
        </button>
      </div>
    </article>
  );
}

