import React, { useState } from "react";
import "./App.css";
import ChatWindow from "./components/ChatWindow";
import CartDrawer from "./components/CartDrawer";

function App() {
  const [cart, setCart] = useState([]);          // [{ ...part, qty }]
  const [cartOpen, setCartOpen] = useState(false);

  const addToCart = (part) => {
    setCart((prev) => {
      const existing = prev.find((i) => i.ps_number === part.ps_number);
      if (existing) {
        return prev.map((i) =>
          i.ps_number === part.ps_number ? { ...i, qty: i.qty + 1 } : i
        );
      }
      return [...prev, { ...part, qty: 1 }];
    });
  };

  const removeFromCart = (ps_number) => {
    setCart((prev) => prev.filter((i) => i.ps_number !== ps_number));
  };

  const cartCount = cart.reduce((n, i) => n + i.qty, 0);

  return (
    <div className="App">
      <header className="ps-header">
        <div className="ps-brand">
          <div className="ps-logo">PS</div>
          <div className="ps-title">
            <span className="ps-title-main">PartSelect</span>
            <span className="ps-title-sub">Parts Assistant</span>
          </div>
        </div>
        <button
          className="ps-cart-button"
          onClick={() => setCartOpen(true)}
          aria-label="Open cart"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2" strokeLinecap="round"
               strokeLinejoin="round">
            <circle cx="9" cy="21" r="1" />
            <circle cx="20" cy="21" r="1" />
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
          </svg>
          {cartCount > 0 && <span className="ps-cart-badge">{cartCount}</span>}
        </button>
      </header>

      <div className="ps-subbar">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" strokeWidth="2" strokeLinecap="round"
             strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        Refrigerator &amp; dishwasher parts only
      </div>

      <ChatWindow addToCart={addToCart} />

      <CartDrawer
        open={cartOpen}
        cart={cart}
        onClose={() => setCartOpen(false)}
        onRemove={removeFromCart}
      />
    </div>
  );
}

export default App;
