import React from "react";
import "./ProductCard.css";

// Generic appliance glyph used when a part has no image_url (seed data has none).
function ApplianceIcon({ type }) {
  if (type === "dishwasher") {
    return (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
           stroke="#7a7a7a" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <rect x="4" y="2" width="16" height="20" rx="1.5" />
        <line x1="4" y1="7" x2="20" y2="7" />
        <circle cx="8" cy="4.5" r="0.6" fill="#7a7a7a" />
        <circle cx="11" cy="4.5" r="0.6" fill="#7a7a7a" />
        <circle cx="12" cy="14" r="3.5" />
      </svg>
    );
  }
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
         stroke="#7a7a7a" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="2" width="14" height="20" rx="1.5" />
      <line x1="5" y1="10" x2="19" y2="10" />
      <line x1="8" y1="5" x2="8" y2="7.5" />
      <line x1="8" y1="13" x2="8" y2="16" />
    </svg>
  );
}

/**
 * A single part card. `banner` (optional) renders a compatibility verdict strip
 * below the card body: { compatible: true|false|null, text }.
 */
function ProductCard({ part, banner, addToCart }) {
  if (!part) return null;

  const bannerClass =
    banner == null ? "" :
    banner.compatible === true ? "compat-yes" :
    banner.compatible === false ? "compat-no" : "compat-unknown";

  const NameTag = part.product_url ? "a" : "span";
  const nameProps = part.product_url
    ? { href: part.product_url, target: "_blank", rel: "noreferrer" }
    : {};

  return (
    <div className="product-card">
      <div className="product-card-body">
        <div className="product-thumb">
          {part.image_url
            ? <img src={part.image_url} alt={part.name} />
            : <ApplianceIcon type={part.appliance_type} />}
        </div>
        <div className="product-info">
          <NameTag className="product-name" {...nameProps}>{part.name}</NameTag>
          <div className="product-meta">
            {part.ps_number} · {part.brand} {part.mfr_part_number}
          </div>
          <div className="product-price-row">
            <span className="product-price">${part.price.toFixed(2)}</span>
            <span className={`product-stock ${part.in_stock ? "in" : "out"}`}>
              {part.in_stock ? "In Stock" : "Out of Stock"}
            </span>
          </div>
        </div>
      </div>

      {banner && (
        <div className={`compat-banner ${bannerClass}`}>
          <span className="compat-title">
            {banner.compatible === true ? "✓ Compatible"
              : banner.compatible === false ? "⚠ Not compatible"
              : "ⓘ Compatibility unknown"}
          </span>
          <span className="compat-reason">{banner.text}</span>
        </div>
      )}

      {addToCart && part.in_stock && (
        <button className="add-to-cart" onClick={() => addToCart(part)}>
          Add to cart
        </button>
      )}
    </div>
  );
}

export default ProductCard;
