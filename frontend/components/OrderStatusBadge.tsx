"use client";

import { ORDER_STATUS_LABELS } from "@/lib/api";
import { OrderStatus } from "@/lib/types";

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return <span className={`status-badge ${status}`}>{ORDER_STATUS_LABELS[status]}</span>;
}

