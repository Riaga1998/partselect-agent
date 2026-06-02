import React from "react";
import "./CartDrawer.css";

function CartDrawer({ open, cart, onClose, onRemove }) {
  const subtotal = cart.reduce((sum, i) => sum + i.price * i.qty, 0);

  return (
    <>
      <div
        className={`cart-overlay ${open ? "open" : ""}`}
        onClick={onClose}
      />
      <aside className={`cart-drawer ${open ? "open" : ""}`}>
        <div className="cart-header">
          <span>Your Cart</span>
          <button className="cart-close" onClick={onClose} aria-label="Close cart">×</button>
        </div>

        {cart.length === 0 ? (
          <p className="cart-empty">Your cart is empty. Add a part from the chat to see it here.</p>
        ) : (
          <>
            <ul className="cart-items">
              {cart.map((item) => (
                <li key={item.ps_number} className="cart-item">
                  <div className="cart-item-info">
                    <span className="cart-item-name">{item.name}</span>
                    <span className="cart-item-meta">
                      {item.ps_number} · ${item.price.toFixed(2)}
                      {item.qty > 1 ? ` × ${item.qty}` : ""}
                    </span>
                  </div>
                  <div className="cart-item-right">
                    <span className="cart-item-line">${(item.price * item.qty).toFixed(2)}</span>
                    <button
                      className="cart-item-remove"
                      onClick={() => onRemove(item.ps_number)}
                      aria-label={`Remove ${item.name}`}
                    >
                      Remove
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            <div className="cart-footer">
              <span>Subtotal</span>
              <span className="cart-subtotal">${subtotal.toFixed(2)}</span>
            </div>
          </>
        )}
      </aside>
    </>
  );
}

export default CartDrawer;
