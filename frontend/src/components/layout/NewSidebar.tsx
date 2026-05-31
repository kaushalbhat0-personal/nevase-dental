import { NavLink } from "react-router-dom";
import { Home, Users, Stethoscope, Calendar, CreditCard } from "lucide-react";

const navItems = [
  { name: "Dashboard", path: "/dashboard", icon: Home },
  { name: "Patients", path: "/patients", icon: Users },
  { name: "Doctors", path: "/doctors", icon: Stethoscope },
  { name: "Appointments", path: "/appointments", icon: Calendar },
  { name: "Billing", path: "/billing", icon: CreditCard },
];

export function Sidebar() {
  return (
    <div className="w-64 border-r border-border bg-card p-4 flex flex-col">
      <div className="flex items-center gap-2 px-2 py-4 mb-6">
        <div className="flex items-center justify-center w-8 h-8 bg-primary rounded-lg">
          <span className="text-primary-foreground text-sm font-bold">N</span>
        </div>
        <h2 className="text-xl font-semibold">Nevase Dental</h2>
      </div>

      <nav className="space-y-1 flex-1">
        {navItems.map((item) => (
          <NavLink
            key={item.name}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`
            }
          >
            <item.icon className="w-4 h-4" />
            {item.name}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
