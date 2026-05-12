export type User = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type Product = {
  id: string;
  name: string;
  slug: string | null;
  description: string;
  price: string;
  stock: number;
  image_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type CartItem = {
  id: string;
  product_id: string;
  product_name: string;
  product_price: string;
  image_url: string | null;
  stock: number;
  quantity: number;
  line_total: string;
};

export type Cart = {
  id: string;
  items: CartItem[];
  total_items: number;
  total_amount: string;
};

export type OrderStatus =
  | "pending"
  | "processing"
  | "ready_for_pickup"
  | "completed"
  | "cancelled";

export type OrderItem = {
  id: string;
  product_id: string;
  product_name: string;
  unit_price: string;
  quantity: number;
  line_total: string;
};

export type Order = {
  id: string;
  order_number: string;
  recipient_name: string;
  delivery_address: string;
  customer_phone: string;
  comment: string | null;
  status: OrderStatus;
  total_amount: string;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
};

