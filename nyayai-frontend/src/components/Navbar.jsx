import { Link, useNavigate, useLocation } from "react-router-dom";
import { Scale } from "lucide-react";
import { useAuth } from "../lib/auth.jsx";

export default function Navbar({ onLoginClick }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <header className="sticky top-0 z-40 bg-stone-50/90 backdrop-blur-sm border-b border-stone-200">
      <nav className="max-w-6xl mx-auto px-5 sm:px-8 flex items-center justify-between h-16">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-forest-700 grid place-items-center">
            <Scale size={15} strokeWidth={2} className="text-white" />
          </div>
          <span className="font-display text-xl font-semibold text-stone-900 tracking-tight">
            Nyay<span className="text-forest-600">AI</span>
          </span>
        </Link>

        <div className="flex items-center gap-2">
          {user ? (
            <>
              <span className="hidden sm:block text-sm text-stone-500 mr-1">{user.name}</span>
              <button onClick={logout} className="text-sm text-stone-500 hover:text-stone-800 px-3 py-2 rounded-lg hover:bg-stone-100 transition-colors cursor-pointer">Sign out</button>
            </>
          ) : (
            <button onClick={onLoginClick} className="text-sm text-stone-500 hover:text-stone-800 px-3 py-2 rounded-lg hover:bg-stone-100 transition-colors cursor-pointer">Log in</button>
          )}
          {pathname !== "/chat" && (
            <button onClick={() => navigate("/chat")}
              className="text-sm font-semibold bg-forest-700 text-white px-5 py-2.5 rounded-full hover:bg-forest-600 transition-colors cursor-pointer">
              {user ? "Open Chat" : "Get Started"}
            </button>
          )}
        </div>
      </nav>
    </header>
  );
}
