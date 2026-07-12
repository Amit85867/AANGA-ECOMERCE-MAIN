import { useState } from "react";
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
import logoMain from "@/assets/images/logo-main.png";
import titleImg from "@/assets/images/logo-title.png";

const MEN_MENU = [
  {
    title: "Topwear",
    items: [
      "T-Shirts",
      "Casual Shirts",
      "Formal Shirts",
      "Polo T-Shirts",
      "Sweatshirts",
      "Hoodies",
    ],
  },
  {
    title: "Bottomwear",
    items: ["Jeans", "Formal Trousers", "Casual Trousers", "Shorts"],
  },
  {
    title: "More",
    items: ["Jackets & Coats", "Innerwear", "Ethnic Wear", "Accessories"],
  },
];

const WOMEN_MENU = [
  {
    title: "Topwear",
    items: ["Tops & Tees", "Shirts & Blouses", "Sweatshirts", "Dresses"],
  },
  { title: "Bottomwear", items: ["Jeans", "Trousers", "Skirts", "Leggings"] },
  {
    title: "Collections",
    items: ["Ethnic Wear", "Winter Wear", "Innerwear", "Accessories"],
  },
];

const KIDS_MENU = [
  {
    title: "Boys",
    items: ["T-Shirts & Shirts", "Jeans & Trousers", "Hoodies & Sweatshirts"],
  },
  {
    title: "Girls",
    items: ["Dresses & Skirts", "Tops & Blouses", "Ethnic Wear"],
  },
];

function MegaDropdown({ columns }) {
  return (
    <div className="invisible opacity-0 group-hover:visible group-hover:opacity-100 absolute top-full left-1/2 -translate-x-1/2 bg-paper border border-line border-t-[3px] border-t-gold min-w-[600px] z-[300] shadow-[0_8px_32px_rgba(0,0,0,0.08)] p-6 grid grid-cols-3 gap-5 transition-all duration-200">
      {columns.map((col) => (
        <div key={col.title}>
          <h4 className="text-[10px] tracking-[2px] uppercase text-gold font-semibold mb-2.5">
            {col.title}
          </h4>
          {col.items.map((item) => (
            <Link
              key={item}
              to="/shop"
              className="block py-1.5 text-[13px] text-ink hover:text-gold transition-colors"
            >
              {item}
            </Link>
          ))}
        </div>
      ))}
    </div>
  );
}

function SmallDropdown({ sections }) {
  return (
    <div className="invisible opacity-0 group-hover:visible group-hover:opacity-100 absolute top-full left-0 bg-paper border border-line border-t-[3px] border-t-gold min-w-[220px] z-[300] shadow-[0_8px_32px_rgba(0,0,0,0.08)] py-2 transition-all duration-200">
      {sections.map((sec, i) => (
        <div key={sec.title}>
          {i > 0 && <hr className="border-line my-1" />}
          <div className="px-5 pt-2 pb-1 text-[10px] tracking-[2px] uppercase text-gold font-semibold">
            {sec.title}
          </div>
          {sec.items.map((item) => (
            <Link
              key={item}
              to="/shop"
              className="block px-5 py-2.5 text-[13px] text-ink hover:bg-cream hover:text-gold transition-colors"
            >
              {item}
            </Link>
          ))}
        </div>
      ))}
    </div>
  );
}

export default function Navbar() {
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

  return (
    <>
      <nav className="bg-paper border-b border-line sticky top-0 z-[150]">
        {/* Top row: Logo left — Search center — Icons right */}
        <div className="flex items-center h-[70px] px-6 lg:px-10">
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden mr-4 text-ink"
          >
            <IconMenu2 size={24} />
          </button>

          <Link to={ROUTES.HOME} className="shrink-0 flex items-center">
            <img src={titleImg} alt="AANGA" className="h-30 object-contain" />
          </Link>

          <div className="flex-1 max-w-[520px] relative mx-auto hidden md:block">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleSearch}
              placeholder="Search for clothes, brands, styles…"
              className="w-full py-3 pl-5 pr-11 border-[1.5px] border-line rounded-full text-sm outline-none focus:border-gold bg-white text-ink"
            />
            <IconSearch
              size={18}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray pointer-events-none"
            />
          </div>

          <div className="flex items-center gap-6 ml-auto shrink-0">
            <Link
              to={isAuthenticated ? "/account" : ROUTES.LOGIN}
              className="flex flex-col items-center gap-0.5 text-xs hover:text-gold transition-colors"
            >
              <IconUser size={22} />
              <span className="hidden sm:block text-[11px]">
                {isAuthenticated ? user?.full_name?.split(" ")[0] : "Account"}
              </span>
            </Link>
            <Link
              to={ROUTES.WISHLIST}
              className="flex flex-col items-center gap-0.5 text-xs hover:text-gold transition-colors"
            >
              <IconHeart size={22} />
              <span className="hidden sm:block text-[11px]">Wishlist</span>
            </Link>
            <Link
              to={ROUTES.CART}
              className="relative flex flex-col items-center gap-0.5 text-xs hover:text-gold transition-colors"
            >
              <IconShoppingBag size={22} />
              {cartCount > 0 && (
                <span className="absolute -top-1.5 -right-1 bg-maroon-light text-white text-[9px] w-[18px] h-[18px] rounded-full flex items-center justify-center font-semibold">
                  {cartCount}
                </span>
              )}
              <span className="hidden sm:block text-[11px]">Cart</span>
            </Link>
          </div>
        </div>

        {/* Bottom row: Nav links */}
        <div className="hidden lg:flex items-center justify-center h-[46px] border-t border-line/50 px-6">
          <ul className="flex items-center h-full list-none gap-0">
            <li className="h-full flex items-center">
              <Link
                to="/"
                className="px-5 text-[13px] tracking-[0.5px] font-medium h-full flex items-center hover:text-gold transition-colors"
              >
                Home
              </Link>
            </li>
            <li className="group relative h-full flex items-center">
              <Link
                to="/shop"
                className="px-5 text-[13px] tracking-[0.5px] font-medium h-full flex items-center hover:text-gold transition-colors gap-1"
              >
                Men <IconChevronDown size={12} />
              </Link>
              <MegaDropdown columns={MEN_MENU} />
            </li>
            <li className="group relative h-full flex items-center">
              <Link
                to="/shop"
                className="px-5 text-[13px] tracking-[0.5px] font-medium h-full flex items-center hover:text-gold transition-colors gap-1"
              >
                Women <IconChevronDown size={12} />
              </Link>
              <MegaDropdown columns={WOMEN_MENU} />
            </li>
            <li className="group relative h-full flex items-center">
              <Link
                to="/shop"
                className="px-5 text-[13px] tracking-[0.5px] font-medium h-full flex items-center hover:text-gold transition-colors gap-1"
              >
                Kids <IconChevronDown size={12} />
              </Link>
              <SmallDropdown sections={KIDS_MENU} />
            </li>
            <li className="h-full flex items-center">
              <Link
                to="/offers"
                className="px-5 text-[13px] tracking-[0.5px] font-medium h-full flex items-center hover:text-gold transition-colors whitespace-nowrap"
              >
                Offers 🔥
              </Link>
            </li>
            <li className="h-full flex items-center">
              <Link
                to="/wholesale"
                className="px-5 text-[13px] tracking-[0.5px] font-medium h-full flex items-center hover:text-gold transition-colors"
              >
                Wholesale
              </Link>
            </li>
          </ul>
        </div>
      </nav>

      {mobileOpen && (
        <div className="fixed inset-0 z-[200] lg:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => {
              setMobileOpen(false);
              setMobileSubmenu(null);
            }}
          />
          <aside className="absolute inset-y-0 left-0 w-[300px] bg-paper overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-line">
              <div className="flex items-center gap-2">
                <img src={logoMain} alt="" className="h-8 w-8 object-contain" />
                <img
                  src={titleImg}
                  alt="AANGA"
                  className="h-7 object-contain"
                />
              </div>
              <button
                onClick={() => {
                  setMobileOpen(false);
                  setMobileSubmenu(null);
                }}
              >
                <IconX size={22} />
              </button>
            </div>
            <div className="p-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search…"
                  className="w-full py-2.5 pl-4 pr-10 border border-line rounded-full text-sm outline-none focus:border-gold"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      navigate("/shop");
                      setMobileOpen(false);
                    }
                  }}
                />
                <IconSearch
                  size={16}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray"
                />
              </div>
            </div>
            <nav className="px-4 pb-6">
              <Link
                to="/"
                onClick={() => setMobileOpen(false)}
                className="block py-3 text-sm font-medium border-b border-line/50"
              >
                Home
              </Link>
              {[
                { label: "Men", key: "men", menu: MEN_MENU },
                { label: "Women", key: "women", menu: WOMEN_MENU },
                { label: "Kids", key: "kids", menu: KIDS_MENU },
              ].map(({ label, key, menu }) => (
                <div key={key}>
                  <button
                    onClick={() =>
                      setMobileSubmenu(mobileSubmenu === key ? null : key)
                    }
                    className="w-full flex items-center justify-between py-3 text-sm font-medium border-b border-line/50"
                  >
                    {label}
                    <IconChevronDown
                      size={16}
                      className={`transition-transform ${mobileSubmenu === key ? "rotate-180" : ""}`}
                    />
                  </button>
                  {mobileSubmenu === key && (
                    <div className="pl-4 pb-2">
                      {menu.map((col) => (
                        <div key={col.title} className="mb-3">
                          <div className="text-[10px] tracking-[2px] uppercase text-gold font-semibold mb-1">
                            {col.title}
                          </div>
                          {col.items.map((item) => (
                            <Link
                              key={item}
                              to="/shop"
                              onClick={() => setMobileOpen(false)}
                              className="block py-1.5 text-[13px] text-gray hover:text-gold"
                            >
                              {item}
                            </Link>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              <Link
                to="/offers"
                onClick={() => setMobileOpen(false)}
                className="block py-3 text-sm font-medium border-b border-line/50"
              >
                Offers 🔥
              </Link>
              <Link
                to="/wholesale"
                onClick={() => setMobileOpen(false)}
                className="block py-3 text-sm font-medium border-b border-line/50"
              >
                Wholesale
              </Link>
              <Link
                to="/contact"
                onClick={() => setMobileOpen(false)}
                className="block py-3 text-sm font-medium border-b border-line/50"
              >
                Contact
              </Link>
              <Link
                to="/about"
                onClick={() => setMobileOpen(false)}
                className="block py-3 text-sm font-medium"
              >
                About
              </Link>
            </nav>
          </aside>
        </div>
      )}
    </>
  );
}
