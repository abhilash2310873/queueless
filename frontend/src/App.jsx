import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { api } from "./api";

function useUser() {
  const [user, setUser] = useState(undefined);
  function refresh() {
    api.me().then((data) => setUser(data.user)).catch(() => setUser(null));
  }
  useEffect(() => { refresh(); }, []);
  return [user, setUser, refresh];
}

function Shell({ user, setUser, children }) {
  async function logout() {
    await api.logout();
    setUser(null);
  }
  return (
    <>
      <nav className="nav">
        <Link className="brand" to="/">QueueLess</Link>
        <Link to="/browse">Browse</Link>
        {user?.role === "student" && <Link to="/cart">Cart</Link>}
        {user?.role === "student" && <Link to="/orders">Orders</Link>}
        {user?.role === "owner" && <Link to="/owner">Kitchen</Link>}
        {user?.role === "admin" && <Link to="/admin">Admin</Link>}
        {user ? <button onClick={logout}>Log out</button> : <Link to="/login">Log in</Link>}
      </nav>
      <main className="wrap">{children}</main>
    </>
  );
}

function Home() {
  return (
    <section className="hero">
      <p className="badge">Campus food courts</p>
      <h1>Order Smart.<br />Skip the Queue.</h1>
      <p className="muted">Browse stalls, pick a pickup slot, and collect with a signed QR ticket.</p>
      <Link className="primary" to="/browse">Browse food</Link>
    </section>
  );
}

function Login({ setUser }) {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      const data = await api.login({ email: form.get("email"), password: form.get("password") });
      setUser(data.user);
      navigate(data.user.role === "owner" ? "/owner" : data.user.role === "admin" ? "/admin" : "/browse");
    } catch (err) {
      setError(err.message);
    }
  }
  return (
    <form className="panel form" onSubmit={submit}>
      <h1>Log in</h1>
      {error && <p className="error">{error}</p>}
      <label>Email<input name="email" required /></label>
      <label>Password<input name="password" type="password" required /></label>
      <button className="primary" type="submit">Log in</button>
      <p><Link to="/register">Create a student account</Link> · <Link to="/reset">Forgot password</Link></p>
      <p className="muted">Student student@college.edu · Owner owner@example.local · Admin admin@example.local · Password Campus@123</p>
    </form>
  );
}

function Reset() {
  const [message, setMessage] = useState("");
  async function ask(event) {
    event.preventDefault();
    const data = await api.forgot({ email: new FormData(event.target).get("email") });
    setMessage(data.message);
  }
  async function change(event) {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await api.reset({ token: form.get("token"), password: form.get("password") });
      setMessage("Password updated. You can log in.");
    } catch (err) {
      setMessage(err.message);
    }
  }
  return (
    <section className="panel form">
      <h1>Reset password</h1>
      <form onSubmit={ask}><label>Email<input name="email" required /></label><button className="primary">Send token</button></form>
      <form onSubmit={change}><label>Token<input name="token" required /></label><label>New password<input name="password" type="password" minLength={8} required /></label><button className="primary">Update password</button></form>
      {message && <p>{message}</p>}
    </section>
  );
}

function Register() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      const data = await api.register({
        name: form.get("name"),
        email: form.get("email"),
        student_id: form.get("student_id"),
        password: form.get("password"),
      });
      setError("");
      setMessage(data.dev_code ? `${data.message} Code: ${data.dev_code}` : data.message);
    } catch (err) {
      setError(err.message);
    }
  }
  return (
    <>
    <form className="panel form" onSubmit={submit}>
      <h1>Register</h1>
      <p className="muted">Any email address can register. The code is printed in the Flask terminal.</p>
      {error && <p className="error">{error}</p>}
      {message && <p>{message}</p>}
      <label>Name<input name="name" required /></label>
      <label>College email<input name="email" required /></label>
      <label>Roll number<input name="student_id" required /></label>
      <label>Password<input name="password" type="password" minLength={8} required /></label>
      <button className="primary" type="submit">Create account</button>
    </form>
    <Verify />
  </>
  );
}

function Verify() {
  const [message, setMessage] = useState("");
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await api.verify({ email: form.get("email"), code: form.get("code") });
      setMessage("Verified. You can log in.");
    } catch (err) {
      setMessage(err.message);
    }
  }
  return (
    <form onSubmit={submit}>
      <h2>Verify email</h2>
      <label>Email<input name="email" required /></label>
      <label>Code<input name="code" required /></label>
      <button className="primary" type="submit">Verify</button>
      {message && <p>{message}</p>}
    </form>
  );
}

function Browse() {
  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({ q: "", category: "", diet: "", available: "", sort: "name" });

  function load(next = filters) {
    api.browse(Object.fromEntries(Object.entries(next).filter(([, value]) => value))).then((data) => {
      setItems(data.items);
      setCategories(data.categories);
    });
  }
  useEffect(() => { load(); }, []);

  async function add(id) {
    try {
      await api.add({ food_id: id, quantity: 1 });
      setError("Added to cart.");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h1>Find food</h1>
      <div className="row">
        <input placeholder="Search" value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value })} />
        <select value={filters.category} onChange={(e) => setFilters({ ...filters, category: e.target.value })}>
          <option value="">Category</option>
          {categories.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
        </select>
        <select value={filters.diet} onChange={(e) => setFilters({ ...filters, diet: e.target.value })}>
          <option value="">Diet</option>
          <option value="veg">Vegetarian</option>
          <option value="nonveg">Non-vegetarian</option>
        </select>
        <select value={filters.sort} onChange={(e) => setFilters({ ...filters, sort: e.target.value })}>
          <option value="name">Name</option>
          <option value="price_asc">Price low-high</option>
          <option value="price_desc">Price high-low</option>
          <option value="rating">Rating</option>
        </select>
        <label><input type="checkbox" checked={filters.available === "1"} onChange={(e) => setFilters({ ...filters, available: e.target.checked ? "1" : "" })} /> Available</label>
        <button className="primary" onClick={() => load()}>Search</button>
      </div>
      {error && <p>{error}</p>}
      <div className="grid">
        {items.map((item) => (
          <article className="card" key={item.id}>
            <p className="badge">{item.stall}</p>
            <h2><Link to={"/food/" + item.id}>{item.name}</Link></h2>
            <p>₹{item.price.toFixed(2)} · {item.prep_time_minutes} min</p>
            <p className="badge">{item.availability}</p>
            <button className="primary" disabled={item.availability !== "AVAILABLE"} onClick={() => add(item.id)}>
              {item.availability === "AVAILABLE" ? "Add to cart" : item.availability}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

function Food({ user }) {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [message, setMessage] = useState("");
  useEffect(() => { api.food(id).then(setItem); }, [id]);
  if (!item) return <p>Loading…</p>;
  return (
    <article className="panel">
      <p className="badge">{item.court} · {item.stall}</p>
      <h1>{item.name}</h1>
      <p>{item.description}</p>
      <p>₹{item.price.toFixed(2)} · stock {item.stock_quantity}</p>
      <p className="badge">{item.availability}</p>
      {user && item.availability === "AVAILABLE" && (
        <button className="primary" onClick={async () => {
          try { await api.add({ food_id: item.id, quantity: 1 }); setMessage("Added to cart."); }
          catch (err) { setMessage(err.message); }
        }}>Add to cart</button>
      )}
      {user && <button onClick={() => api.favorite({ target_type: "food", target_id: item.id })}>Favorite</button>}
      {message && <p>{message}</p>}
    </article>
  );
}

function Cart({ user }) {
  const [cart, setCart] = useState(null);
  const [message, setMessage] = useState("");
  const [method, setMethod] = useState("CASH");
  const [slotId, setSlotId] = useState("");
  const navigate = useNavigate();
  function load() { api.cart().then((data) => { setCart(data); if (!slotId && data.recommendation) setSlotId(String(data.recommendation.slot_id)); }); }
  useEffect(() => { if (user) load(); }, [user]);
  if (!user) return <Navigate to="/login" />;
  if (!cart) return <p>Loading…</p>;
  async function checkout() {
    try {
      const order = await api.checkout({ slot_id: Number(slotId), method });
      if (method === "ONLINE" && order.payment_status === "PENDING") {
        navigate("/pay/" + order.id);
      } else {
        navigate("/orders/" + order.id);
      }
    } catch (err) {
      setMessage(err.message);
    }
  }
  return (
    <section className="panel">
      <h1>Cart</h1>
      <p className="muted">One stall per cart, so the queue belongs to one kitchen.</p>
      {cart.stall && <p>{cart.court} · {cart.stall}</p>}
      {cart.problems.map((problem) => <p className="error" key={problem}>{problem}</p>)}
      {cart.items.map((line) => (
        <div className="row" key={line.food_id}>
          <strong>{line.name}</strong>
          <span>₹{line.price.toFixed(2)}</span>
          <input style={{ width: "4rem" }} defaultValue={line.quantity} onBlur={(e) => api.update({ food_id: line.food_id, quantity: Number(e.target.value) }).then(load)} />
        </div>
      ))}
      <p>Total ₹{cart.total.toFixed(2)}</p>
      {cart.recommendation && <p>Recommended slot: {cart.recommendation.label}. {cart.recommendation.reason}</p>}
      <label>Pickup slot
        <select value={slotId} onChange={(e) => setSlotId(e.target.value)}>
          <option value="">Choose</option>
          {cart.slots.map((slot) => <option key={slot.id} value={slot.id} disabled={slot.full}>{slot.label} · {slot.full ? "FULL" : slot.spaces_left + " left"}</option>)}
        </select>
      </label>
      <label>Payment
        <select value={method} onChange={(e) => setMethod(e.target.value)}>
          <option value="CASH">Pay at cash counter</option>
          <option value="ONLINE">Online payment</option>
        </select>
      </label>
      {message && <p className="error">{message}</p>}
      <button className="primary" disabled={!cart.items.length || !slotId} onClick={checkout}>Place order</button>
      <button onClick={() => api.clear().then(load)}>Clear</button>
    </section>
  );
}

function Pay() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  async function finish(result) {
    try {
      await api.pay(id, result);
      navigate("/orders/" + id);
    } catch (err) {
      setError(err.message);
    }
  }
  return (
    <section className="panel form">
      <h1>Pay online</h1>
      <p className="muted">Confirm the payment to receive your queue number. Card details are not stored.</p>
      {error && <p className="error">{error}</p>}
      <button className="primary" onClick={() => finish("success")}>Pay and confirm order</button>
      <button onClick={() => finish("failure")}>Cancel payment</button>
    </section>
  );
}

function Orders() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.orders().then((data) => setRows(data.orders)); }, []);
  return (
    <section>
      <h1>Your orders</h1>
      {rows.map((order) => (
        <p key={order.id}><Link to={"/orders/" + order.id}>{order.queue_number || order.id.slice(0, 8)}</Link> · {order.stall} · ₹{order.total.toFixed(2)} · {order.status} · {order.payment_status}</p>
      ))}
    </section>
  );
}

function OrderPage() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [message, setMessage] = useState("");
  function load() { api.order(id).then(setOrder).catch((err) => setMessage(err.message)); }
  useEffect(() => { load(); const timer = setInterval(load, 8000); return () => clearInterval(timer); }, [id]);
  if (!order) return <p>{message || "Loading…"}</p>;
  const steps = ["PENDING", "ACCEPTED", "PREPARING", "READY", "COLLECTED"];
  return (
    <article className="panel">
      <h1>{order.queue_number || "Payment pending"}</h1>
      <p>{order.court} · {order.stall}</p>
      <ol>{steps.map((step) => <li key={step}><strong>{order.status === step ? step : ""}</strong>{order.status === step ? "" : step}</li>)}</ol>
      <p>Payment: {order.payment_status}</p>
      {order.payment_status === "CASH_PENDING" && <p>PAYMENT PENDING until the stall records cash.</p>}
      {order.snapshot && <p>Position {order.snapshot.position}. Ahead {order.snapshot.orders_ahead}. Wait {order.snapshot.estimated_wait_minutes} min.</p>}
      {order.items.map((item) => <p key={item.name}>{item.quantity} × {item.name}</p>)}
      {order.token && <p>Pickup token: <code>{order.token}</code></p>}
      {order.status === "PENDING" && <button onClick={() => api.cancel(order.id).then(load)}>Cancel</button>}
      {order.status === "COLLECTED" && !order.has_review && (
        <form onSubmit={(event) => { event.preventDefault(); api.review(order.id, { rating: Number(new FormData(event.target).get("rating")), text: new FormData(event.target).get("text") }).then(load); }}>
          <input name="rating" type="number" min="1" max="5" required />
          <input name="text" placeholder="Optional review" />
          <button className="primary" type="submit">Save review</button>
        </form>
      )}
    </article>
  );
}

function Owner() {
  const [data, setData] = useState(null);
  const [menu, setMenu] = useState([]);
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  function load() {
    api.ownerOrders().then(setData);
    api.ownerMenu().then((rows) => setMenu(rows.items || []));
  }
  useEffect(() => { load(); }, []);
  if (!data) return <p>Loading…</p>;
  async function act(id, action) {
    try {
      await api.ownerAction(id, action, action === "collect" ? { token } : {});
      setMessage("Updated.");
      load();
    } catch (err) {
      setMessage(err.message);
    }
  }
  return (
    <section>
      <h1>{data.stall || "No stall"} orders</h1>
      {message && <p>{message}</p>}
      <h2>Menu</h2>
      <div className="grid">
        {menu.map((item) => (
          <article className="card" key={item.id}>
            <h2>{item.name}</h2>
            <p className="badge">{item.availability}</p>
            <p>Stock {item.stock_quantity}</p>
          </article>
        ))}
      </div>
      <label>Pickup token<input value={token} onChange={(e) => setToken(e.target.value)} /></label>
      {data.demand && <p>Demand this hour: {data.demand.level}. {data.demand.note}</p>}
      {(data.insights || []).map((line) => <p key={line}>{line}</p>)}
      <FoodForm onDone={load} />
      {data.orders.map((order) => (
        <article className="card" key={order.id}>
          <h2>{order.queue_number || "Unpaid online"} · {order.status}</h2>
          <p>{order.payment_status} · ₹{order.total.toFixed(2)}</p>
          <div className="row">
            {["cash", "accept", "preparing", "ready", "reject", "collect"].map((action) => (
              <button key={action} onClick={() => act(order.id, action)}>{action}</button>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}

function FoodForm({ onDone }) {
  const [message, setMessage] = useState("");
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await api.createFood({
        name: form.get("name"),
        price: form.get("price"),
        category_id: Number(form.get("category_id")),
        prep_time_minutes: Number(form.get("prep")),
        stock_quantity: Number(form.get("stock")),
        is_vegetarian: form.get("veg") === "on",
      });
      setMessage("Food added.");
      onDone();
    } catch (err) {
      setMessage(err.message);
    }
  }
  return (
    <form className="card" onSubmit={submit}>
      <h2>Add food</h2>
      <input name="name" placeholder="Name" required />
      <input name="price" placeholder="Price" required />
      <input name="category_id" placeholder="Category id" required />
      <input name="prep" placeholder="Minutes" defaultValue="8" />
      <input name="stock" placeholder="Stock" defaultValue="10" />
      <label><input name="veg" type="checkbox" defaultChecked /> Vegetarian</label>
      <button className="primary">Save food</button>
      {message && <p>{message}</p>}
    </form>
  );
}

function Admin() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.admin().then(setData).catch((err) => setError(err.message)); }, []);
  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading…</p>;
  return (
    <section>
      <h1>Platform</h1>
      <p>Students {data.students}. Owners {data.owners}. Orders {data.orders}. Revenue ₹{data.revenue.toFixed(2)}.</p>
      <div className="grid">
        <article className="card"><h2>Courts</h2>{data.courts.map((court) => <p key={court.id}>{court.name} · {court.status}</p>)}</article>
        <article className="card"><h2>Stalls</h2>{data.stalls.map((stall) => <p key={stall.id}>{stall.name} · {stall.status}</p>)}</article>
      </div>
      <form className="card" onSubmit={async (event) => {
        event.preventDefault();
        const form = new FormData(event.target);
        await api.createCourt({ name: form.get("name"), location: form.get("location"), opening_time: "08:00", closing_time: "21:00" });
        event.target.reset();
      }}>
        <h2>New food court</h2>
        <input name="name" placeholder="Name" required />
        <input name="location" placeholder="Location" required />
        <button className="primary">Create court</button>
      </form>
      <form className="card" onSubmit={async (event) => {
        event.preventDefault();
        const form = new FormData(event.target);
        await api.createStall({ food_court_id: Number(form.get("food_court_id")), name: form.get("name"), location: form.get("location"), contact: form.get("contact"), opening_time: "09:00", closing_time: "21:00" });
        event.target.reset();
      }}>
        <h2>New stall</h2>
        <input name="food_court_id" placeholder="Food court id" required />
        <input name="name" placeholder="Stall name" required />
        <input name="location" placeholder="Location" required />
        <input name="contact" placeholder="Contact" required />
        <button className="primary">Create stall</button>
      </form>
      <h2>Users</h2>
      {data.users.map((user) => <p key={user.id}>{user.name} · {user.email} · {user.role}</p>)}
    </section>
  );
}

export default function App() {
  const [user, setUser] = useUser();
  if (user === undefined) return <p className="wrap">Loading QueueLess…</p>;
  return (
    <Shell user={user} setUser={setUser}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login setUser={setUser} />} />
        <Route path="/register" element={<Register />} />
        <Route path="/reset" element={<Reset />} />
        <Route path="/browse" element={<Browse />} />
        <Route path="/food/:id" element={<Food user={user} />} />
        <Route path="/cart" element={<Cart user={user} />} />
        <Route path="/pay/:id" element={<Pay />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/orders/:id" element={<OrderPage />} />
        <Route path="/owner" element={user?.role === "owner" ? <Owner /> : <Navigate to="/login" />} />
        <Route path="/admin" element={user?.role === "admin" ? <Admin /> : <Navigate to="/login" />} />
      </Routes>
    </Shell>
  );
}
