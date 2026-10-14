async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

export const api = {
  me: () => request("/api/v1/me"),
  login: (body) => request("/api/v1/auth/login", { method: "POST", body }),
  register: (body) => request("/api/v1/auth/register", { method: "POST", body }),
  verify: (body) => request("/api/v1/auth/verify", { method: "POST", body }),
  logout: () => request("/api/v1/auth/logout", { method: "POST" }),
  browse: (params) => request("/api/v1/browse?" + new URLSearchParams(params)),
  food: (id) => request("/api/v1/food/" + id),
  cart: () => request("/api/v1/cart"),
  add: (body) => request("/api/v1/cart/add", { method: "POST", body }),
  update: (body) => request("/api/v1/cart/update", { method: "POST", body }),
  clear: () => request("/api/v1/cart/clear", { method: "POST" }),
  checkout: (body) => request("/api/v1/checkout", { method: "POST", body }),
  pay: (id, result) => request(`/api/v1/payment/${id}/${result}`, { method: "POST" }),
  orders: () => request("/api/v1/orders"),
  order: (id) => request("/api/v1/orders/" + id),
  cancel: (id) => request(`/api/v1/orders/${id}/cancel`, { method: "POST" }),
  review: (id, body) => request(`/api/v1/orders/${id}/review`, { method: "POST", body }),
  favorites: () => request("/api/v1/favorites"),
  favorite: (body) => request("/api/v1/favorites", { method: "POST", body }),
  ownerOrders: () => request("/api/v1/owner/orders"),
  ownerAction: (id, action, body) => request(`/api/v1/owner/orders/${id}/${action}`, { method: "POST", body: body || {} }),
  ownerMenu: () => request("/api/v1/owner/menu"),
  admin: () => request("/api/v1/admin/summary"),
  createCourt: (body) => request("/api/v1/admin/courts", { method: "POST", body }),
  createStall: (body) => request("/api/v1/admin/stalls", { method: "POST", body }),
  createCategory: (body) => request("/api/v1/admin/categories", { method: "POST", body }),
  createFood: (body) => request("/api/v1/owner/food", { method: "POST", body }),
  forgot: (body) => request("/api/v1/auth/forgot", { method: "POST", body }),
  reset: (body) => request("/api/v1/auth/reset", { method: "POST", body }),
};
