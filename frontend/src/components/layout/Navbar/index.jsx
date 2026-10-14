import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  IconSearch,
  IconUser,
  IconHeart,
  IconShoppingBag,
  IconMenu2,
  IconX,
  IconChevronDown,
} from "@tabler/icons-react";
import { useCartStore, selectCartCount } from "@/store/useCartStore";
import { useAuthStore } from "@/store/useAuthStore";
import { ROUTES } from "@/utils/constants";
import { useLayoutStore } from "@/store/useLayoutStore";
import { useProductStore } from "@/store/useProductStore";
import { useSetting } from "@/store/useSettingsStore";
import logoMain from "@/assets/images/logo-main.webp";
// 168px copy: three times the 56px it is shown at here, a third of the bytes.
import titleImg from "@/assets/images/logo-title-168.webp";

// Shown until the menu has loaded. The real one is edited under Admin → Menus.
const FALLBACK_LINKS = [
  { label: "Shop", url: "/shop" },
  { label: "Offers", url: "/offers" },
];

// A menu link that points at a category (/shop?category=men) gets that
// category's sub-categories as a drop-down, straight from the catalogue.
const categoryOf = (url, categories) => {
  const match = /^\/shop\?category=([a-z0-9-]+)$/.exec(url || "");
  return match ? categories.find((c) => c.slug === match[1]) : null;
};

const isExternal = (url) => /^https?:|^mailto:|^tel:/.test(url || "");

const navLinkClass = ({ isActive }) =>
  [
    "relative py-2 text-sm font-medium uppercase tracking-[0.05em] transition-colors",
    "after:absolute after:left-0 after:-bottom-0.5 after:h-px after:bg-fg after:transition-all",
    isActive
      ? "text-fg after:w-full"
      : "text-muted hover:text-fg after:w-0 hover:after:w-full",
  ].join(" ");

function Dropdown({ category }) {
  return (
    <div
      className={[
        "invisible opacity-0 translate-y-1 group-hover:visible group-hover:opacity-100 group-hover:translate-y-0",
        "group-focus-within:visible group-focus-within:opacity-100 group-focus-within:translate-y-0",
        "absolute top-full left-1/2 -translate-x-1/2 mt-2 z-[300]",
        "bg-card rounded-card shadow-lift border border-hairline p-7",
        "transition-all duration-200 min-w-[260px]",
      ].join(" ")}
    >
      <p className="text-xs tracking-[0.1em] uppercase text-muted font-semibold mb-3">{category.name}</p>
      <div className={category.children.length > 5 ? "grid grid-cols-2 gap-x-8 min-w-[420px]" : ""}>
        {category.children.map((child) => (
          <Link
            key={child.id}
            to={`/shop?category=${child.slug}`}
            className="block py-1.5 text-sm text-muted hover:text-fg transition-colors"
          >
            {child.name}
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function Navbar() {
  const headerLinks = useLayoutStore((st) => st.navigation.header);
  const categories = useProductStore((st) => st.categories);
  const fetchCategories = useProductStore((st) => st.fetchCategories);
  const s = useSetting();
  const storeName = s("store_name", "AANGA");
  const logo = s("logo_url") || titleImg;
  const links = headerLinks.length ? headerLinks : FALLBACK_LINKS;
  useEffect(() => { fetchCategories(); }, [fetchCategories]);

  const cartCount = useCartStore(selectCartCount);
  const { isAuthenticated, user } = useAuthStore();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mobileSubmenu, setMobileSubmenu] = useState(null);
  const [query, setQuery] = useState("");

  const handleSearch = (e) => {
    if (e.key === "Enter" && query.trim()) {
      navigate(`/shop?q=${encodeURIComponent(query.trim())}`);
      setQuery("");
    }
  };

  const closeMobile = () => {
    setMobileOpen(false);
    setMobileSubmenu(null);
  };

  return (
    <>
      <nav className="glass sticky top-0 z-[150] border-b border-hairline">
        <div className="max-w-[1440px] mx-auto flex items-center gap-6 h-[80px] px-3 md:px-5 lg:px-6">
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden text-fg"
            aria-label="Open menu"
          >
            <IconMenu2 size={24} />
          </button>

          <Link to={ROUTES.HOME} className="shrink-0 flex items-center mr-2">
            <img src={logo} alt={storeName} width="56" height="56" className="h-12 w-12 md:h-14 md:w-14 object-contain" />
          </Link>

          {/* Primary navigation */}
          <ul className="hidden lg:flex items-center gap-7 list-none h-full">
            {links.map((link) => {
              const category = categoryOf(link.url, categories);
              const hasMenu = category?.children?.length > 0;
              return (
                <li key={`${link.label}-${link.url}`} className={`h-full flex items-center ${hasMenu ? "group relative" : ""}`}>
                  {isExternal(link.url) ? (
                    <a href={link.url} target="_blank" rel="noreferrer" className={navLinkClass({ isActive: false })}>{link.label}</a>
                  ) : (
                    <Link to={link.url} className={navLinkClass({ isActive: false })}>
                      <span className="flex items-center gap-1">
                        {link.label} {hasMenu && <IconChevronDown size={13} aria-hidden="true" />}
                      </span>
                    </Link>
                  )}
                  {hasMenu && <Dropdown category={category} />}
                </li>
              );
            })}
          </ul>

          {/* Search — pill, per the design system */}
          <div className="flex-1 max-w-[320px] relative ml-auto hidden md:block">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleSearch}
              placeholder="Search collections…"
              aria-label="Search products"
              className="w-full h-11 pl-11 pr-4 bg-fill rounded-full text-sm outline-none
                         border border-transparent focus:border-primary focus:bg-card
                         text-fg placeholder:text-subtle transition-colors"
            />
            <IconSearch
              size={18}
              stroke={1.5}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-muted pointer-events-none"
            />
          </div>

          <div className="flex items-center gap-5 md:ml-0 ml-auto shrink-0">
            <Link
              to={ROUTES.WISHLIST}
              aria-label="Wishlist"
              className="text-fg hover:text-accent transition-colors"
            >
              <IconHeart size={22} stroke={1.5} />
            </Link>
            <Link
              to={ROUTES.CART}
              aria-label={`Cart${cartCount > 0 ? `, ${cartCount} items` : ""}`}
              className="relative text-fg hover:text-accent transition-colors"
            >
              <IconShoppingBag size={22} stroke={1.5} />
              {cartCount > 0 && (
                <span className="absolute -top-1.5 -right-1.5 bg-accent text-white text-xs
                                 min-w-[18px] h-[18px] px-1 rounded-full flex items-center
                                 justify-center font-semibold">
                  {cartCount}
                </span>
              )}
            </Link>
            <Link
              to={isAuthenticated ? "/account/orders" : ROUTES.LOGIN}
              aria-label={isAuthenticated ? "Account" : "Sign in"}
              className="flex items-center gap-2 text-fg hover:text-accent transition-colors"
            >
              <IconUser size={22} stroke={1.5} />
              {isAuthenticated && (
                <span className="hidden xl:block text-sm font-medium">
                  {user?.full_name?.split(" ")[0]}
                </span>
              )}
            </Link>
          </div>
        </div>
      </nav>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-[200] lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={closeMobile} />
          <aside className="absolute inset-y-0 left-0 w-[320px] bg-card overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-hairline">
              <div className="flex items-center gap-2">
                <img src={logoMain} alt="" width="32" height="32" className="h-8 w-8 object-contain" />
                <img src={logo} alt={storeName} width="28" height="28" className="h-7 w-7 object-contain" />
              </div>
              <button onClick={closeMobile} aria-label="Close menu" className="text-fg">
                <IconX size={22} />
              </button>
            </div>

            <div className="p-5">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search collections…"
                  aria-label="Search products"
                  className="w-full h-11 pl-11 pr-4 bg-fill rounded-full text-sm outline-none
                             border border-transparent focus:border-primary text-fg
                             placeholder:text-subtle"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      navigate("/shop");
                      closeMobile();
                    }
                  }}
                />
                <IconSearch
                  size={18}
                  stroke={1.5}
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-muted"
                />
              </div>
            </div>

            <nav className="px-5 pb-8">
              <Link
                to="/"
                onClick={closeMobile}
                className="block py-3.5 text-sm font-medium uppercase tracking-[0.05em] text-fg border-b border-hairline"
              >
                Home
              </Link>
              {links.map((link) => {
                const category = categoryOf(link.url, categories);
                const key = `${link.label}-${link.url}`;
                if (!category?.children?.length) {
                  return isExternal(link.url) ? (
                    <a key={key} href={link.url} target="_blank" rel="noreferrer"
                      className="block py-3.5 text-sm font-medium uppercase tracking-[0.05em] text-fg border-b border-hairline">
                      {link.label}
                    </a>
                  ) : (
                    <Link key={key} to={link.url} onClick={closeMobile}
                      className="block py-3.5 text-sm font-medium uppercase tracking-[0.05em] text-fg border-b border-hairline">
                      {link.label}
                    </Link>
                  );
                }
                return (
                  <div key={key}>
                    <button
                      onClick={() => setMobileSubmenu(mobileSubmenu === key ? null : key)}
                      aria-expanded={mobileSubmenu === key}
                      className="w-full flex items-center justify-between py-3.5 text-sm font-medium
                                 uppercase tracking-[0.05em] text-fg border-b border-hairline"
                    >
                      {link.label}
                      <IconChevronDown size={16} className={`transition-transform ${mobileSubmenu === key ? "rotate-180" : ""}`} />
                    </button>
                    {mobileSubmenu === key && (
                      <div className="pl-4 py-3">
                        <Link to={link.url} onClick={closeMobile} className="block py-1.5 text-sm font-medium text-fg">
                          All {category.name}
                        </Link>
                        {category.children.map((child) => (
                          <Link key={child.id} to={`/shop?category=${child.slug}`} onClick={closeMobile}
                            className="block py-1.5 text-sm text-muted hover:text-fg">
                            {child.name}
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </nav>
          </aside>
        </div>
      )}
    </>
  );
}
