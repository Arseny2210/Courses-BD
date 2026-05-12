'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useDeferredValue, useEffect, useState } from 'react'

import { useAuth } from '@/components/AuthProvider'
import { ProductCard } from '@/components/ProductCard'
import { apiRequest } from '@/lib/api'
import { Product } from '@/lib/types'

export default function HomePage() {
	const router = useRouter()
	const { token, user, ready } = useAuth()
	const [products, setProducts] = useState<Product[]>([])
	const [search, setSearch] = useState('')
	const deferredSearch = useDeferredValue(search)
	const [loading, setLoading] = useState(true)
	const [message, setMessage] = useState<string | null>(null)
	const [busyProductId, setBusyProductId] = useState<string | null>(null)

	useEffect(() => {
		let active = true
		setLoading(true)
		setMessage(null)

		const params = new URLSearchParams()
		if (deferredSearch.trim()) {
			params.set('search', deferredSearch.trim())
		}

		apiRequest<Product[]>(
			`/api/products${params.toString() ? `?${params.toString()}` : ''}`,
		)
			.then(response => {
				if (active) {
					setProducts(response)
				}
			})
			.catch((error: Error) => {
				if (active) {
					setMessage(error.message)
				}
			})
			.finally(() => {
				if (active) {
					setLoading(false)
				}
			})

		return () => {
			active = false
		}
	}, [deferredSearch])

	async function handleAddToCart(productId: string) {
		if (!ready) {
			return
		}

		if (!token) {
			router.push('/login')
			return
		}

		setBusyProductId(productId)
		setMessage(null)

		try {
			await apiRequest('/api/cart/items', {
				method: 'POST',
				token,
				body: JSON.stringify({ product_id: productId, quantity: 1 }),
			})
			setMessage('Товар добавлен в корзину')
		} catch (error) {
			setMessage(
				error instanceof Error ? error.message : 'Не удалось добавить товар',
			)
		} finally {
			setBusyProductId(null)
		}
	}

	const heroTitle = user?.is_admin
		? 'Управляй каталогом, остатками и заказами в одном месте'
		: 'Выбирай технику, оформляй заказ и отслеживай каждый этап'

	const heroSubtitle = user?.is_admin
		? 'Обновляй товары, контролируй наличие на складе и меняй статусы заказов из панели управления.'
		: 'Ноутбуки, смартфоны, аксессуары и игровая техника с быстрым оформлением и прозрачным статусом заказа.'

	return (
		<div className='page-stack'>
			<section className='hero-card'>
				<div className='hero-main'>
					<h1>{heroTitle}</h1>
					<p className='hero-copy'>{heroSubtitle}</p>

					<div className='hero-points'>
						<span className='hero-point'>Быстрое оформление</span>
						<span className='hero-point'>Живые остатки</span>
						<span className='hero-point'>Контроль статуса заказа</span>
					</div>
				</div>

				<div className='hero-side'>
					<div className='hero-actions'>
						<Link href='/cart' className='primary-button link-button'>
							Открыть корзину
						</Link>
						<Link href='/orders' className='ghost-button link-button'>
							Мои заказы
						</Link>
						{user?.is_admin ? (
							<Link href='/admin' className='ghost-button link-button'>
								Панель управления
							</Link>
						) : null}
					</div>

					<div className='hero-metrics'>
						<div className='metric-card'>
							<strong>{products.length || '6+'}</strong>
							<span>Товаров в каталоге</span>
						</div>
						<div className='metric-card'>
							<strong>{user?.is_admin ? 'Admin' : 'Online'}</strong>
							<span>
								{user?.is_admin
									? 'Расширенный доступ'
									: 'Покупки без лишних шагов'}
							</span>
						</div>
						<div className='metric-card accent'>
							<strong>24/7</strong>
							<span>Отслеживание статуса заказа</span>
						</div>
					</div>
				</div>
			</section>

			<section className='panel'>
				<div className='section-head'>
					<div>
						<p className='eyebrow'>Каталог</p>
						<h2>Актуальные предложения</h2>
					</div>
					<input
						className='search-input'
						placeholder='Поиск по названию и описанию'
						value={search}
						onChange={event => setSearch(event.target.value)}
					/>
				</div>

				{message ? <p className='inline-message'>{message}</p> : null}

				{loading ? (
					<div className='empty-state'>Загружаем каталог...</div>
				) : products.length === 0 ? (
					<div className='empty-state'>
						Ничего не найдено. Попробуй другой поисковый запрос.
					</div>
				) : (
					<div className='product-grid'>
						{products.map(product => (
							<ProductCard
								key={product.id}
								product={product}
								onAddToCart={handleAddToCart}
								busy={busyProductId === product.id}
							/>
						))}
					</div>
				)}
			</section>
		</div>
	)
}
