import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";
import { Eye, EyeOff } from "lucide-react";

const STATUS_LABELS = {
  available: "Available",
  booked: "Currently in use",
  maintenance: "Under Maintenance",
  unavailable: "Unavailable",
};

const BOOKING_LABELS = {
  pending: "Pending approval",
  confirmed: "Confirmed",
  rejected: "Rejected",
  cancelled: "Cancelled",
  no_show: "No-show released",
};




function StatusPill({ status }) {
  return (
    <span className={`status status-${status}`}>
      <span className="status-dot" />
      {STATUS_LABELS[status] || status}
    </span>
  );
}

function BookingBadge({ status }) {
  return (
    <span className={`booking-state booking-${status}`}>
      {BOOKING_LABELS[status] || status}
    </span>
  );
}

function Toasts({ items }) {
  return (
    <div className="toast-stack">
      {items.map((item) => (
        <div key={item.id} className={`toast toast-${item.kind}`}>
          {item.message}
        </div>
      ))}
    </div>
  );
}

function Modal({ title, subtitle, onClose, children }) {
  useEffect(() => {
    const handler = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="modal">
        <div className="modal-head">
          <div>
            <h3>{title}</h3>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function AuthScreen({ onAuthed, notify }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    phone_number: "",
    asAdmin: false,
    invite_code: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);


  const update = (key) => (event) => {
    const value =
      event.target.type === "checkbox"
        ? event.target.checked
        : event.target.value;

    setForm((current) => ({
      ...current,
      [key]: value,
    }));
  };

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");



    try {
      if (mode === "login") {
        const data = await api("/api/auth/login", {
          method: "POST",
          body: {
            email: form.email,
            password: form.password,
          },
        });
        notify("Signed in successfully.", "success");
        onAuthed(data.user);
      } else {
        const data = await api("/api/auth/register", {
          method: "POST",
          body: {
            name: form.name,
            email: form.email,
            password: form.password,
            phone_number: form.phone_number,
            role: form.asAdmin ? "admin" : "student",
            invite_code: form.invite_code,
            email_reminders: true,
            sms_reminders: false,
          },
        });
        notify("Account created.", "success");
        onAuthed(data.user);
      }
    } catch (error) {
      setError(error.message);
    } finally { 
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-hero">
        <div className="eyebrow">CAMPUSFLOW / RESOURCE-OS</div>
        <h1>
          Every campus resource.
          <span> One transparent booking flow.</span>
        </h1>
        <p>
          Discover equipment, reserve conflict-free slots, route selected
          resources through approval, receive reminders, and automatically
          release no-show bookings.
        </p>

        <div className="hero-statuses">
          <StatusPill status="available" />
          <StatusPill status="booked" />
          <StatusPill status="maintenance" />
          <StatusPill status="unavailable" />
        </div>

        <div className="hero-metrics">
          <div>
            <strong>01</strong>
            <span>Collision prevention</span>
          </div>
          <div>
            <strong>02</strong>
            <span>Approval workflow</span>
          </div>
          <div>
            <strong>03</strong>
            <span>Reminder + no-show automation</span>
          </div>
        </div>
      </section>

      <section className="auth-panel">
        <form className="auth-card" onSubmit={submit}>
          <div className="brand">
            <span className="brand-dot" />
            CampusFlow
          </div>

          <h2>{mode === "login" ? "Welcome" : "Create your account"}</h2>
          <p className="muted">
            {mode === "login"
              ? "Sign in to manage campus resource bookings."
              : "Students can book resources; admins can manage approvals and inventory."}
          </p>

          {error && <div className="alert alert-error">{error}</div>}

          {mode === "register" && (
            <>
              <label className="field">
                <span>Full name</span>
                <input
                  value={form.name}
                  onChange={update("name")}
                  placeholder="Your name"
                  required
                />
              </label>

              <label className="field">
                <span>Phone number (optional, for SMS reminders)</span>
                <input
                  value={form.phone_number}
                  onChange={update("phone_number")}
                  placeholder="+91..."
                />
              </label>
            </>
          )}

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={form.email}
              onChange={update("email")}
              placeholder="you@university.edu"
              required
            />
          </label>

          <label className="field">
            <span>Password</span>
            <div className="password-wrapper">
              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={update("password")}
                minLength={6}
                placeholder="At least 6 characters"
                required
                />
              <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                {showPassword ? <EyeOff size={20} color="black" /> : <Eye size={20} />}
              </button>
            </div>
          </label>

          {mode === "register" && (
            <>
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={form.asAdmin}
                  onChange={update("asAdmin")}
                />
                <span>Register as lab admin</span>
              </label>

              {form.asAdmin && (
                <label className="field">
                  <span>Admin invite code</span>
                  <input
                    value={form.invite_code}
                    onChange={update("invite_code")}
                    placeholder="Provided by institution"
                  />
                </label>
              )}
            </>
          )}

          <button className="btn btn-primary btn-block" disabled={busy}>
            {busy
              ? "Please wait…"
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </button>

          <button
            type="button"
            className="switch-link"
            onClick={() => {
              setMode((current) =>
                current === "login" ? "register" : "login"
              );
              setError("");
            }}
          >
            {mode === "login"
              ? "New to CampusFlow? Create an account"
              : "Already registered? Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}

function AppShell({
  user,
  tabs,
  activeTab,
  setActiveTab,
  onLogout,
  children,
}) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="brand brand-light">
            <span className="brand-dot" />
            CampusFlow
          </div>
          <div className="side-kicker">RESOURCE BOOKING SYSTEM</div>
        </div>

        <nav className="side-nav">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              className={activeTab === tab.key ? "active" : ""}
              onClick={() => setActiveTab(tab.key)}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-user">
          <div className="avatar">{user.name?.[0]?.toUpperCase() || "U"}</div>
          <div className="sidebar-user-copy">
            <strong>{user.name}</strong>
            <span>{user.role}</span>
          </div>
          <button className="signout" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </aside>

      <div className="mobile-topbar">
        <div className="brand">
          <span className="brand-dot" />
          CampusFlow
        </div>
        <select
          value={activeTab}
          onChange={(event) => {
            const value = event.target.value;

            if (value === "logout") {
              onLogout();
            } else {
              setActiveTab(value);
            }
          }}
        >
          {tabs.map((tab) => (
          <option key={tab.key} value={tab.key}>
            {tab.label}
          </option>
          ))}
          <option value="logout">
            Sign out
          </option>
        </select>
      </div>

      <section className="main-area">{children}</section>
    </div>
  );
}

function PageHeader({ eyebrow, title, subtitle, action }) {
  return (
    <header className="page-header">
      <div>
        <div className="page-eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action}
    </header>
  );
}

function ResourceCard({ resource, onBook }) {
  return (
    <article className="resource-card">
      <div className="resource-top">
        <span className="asset-id">
          #{String(resource.id).padStart(4, "0")}
        </span>
        <StatusPill status={resource.status} />
      </div>

      <div>
        <div className="card-badge-row">
          {resource.requires_approval && (
            <span className="approval-tag">ADMIN APPROVAL</span>
          )}
        </div>

        <h3>{resource.name}</h3>
        <p className="resource-meta">
          {resource.type} · {resource.category}
        </p>
        <p className="resource-lab">{resource.lab}</p>
        {resource.description && (
          <p className="resource-desc">{resource.description}</p>
        )}
      </div>

      {resource.slot_available !== undefined && (
        <div className={resource.slot_available ? "slot-ok" : "slot-unavailable"}>
          {resource.slot_available
            ? "Available for selected slot"
            : "Conflict in selected slot"}
        </div>
      )}

      <div className="resource-foot">
        <span>Max {resource.max_booking_minutes} min</span>
        <button
              className="btn btn-primary btn-small"
              disabled={
                resource.status === "maintenance" ||
                resource.status === "unavailable"
              }
              onClick={() => onBook(resource)}
            >
              {resource.status === "booked"
                ? "Book another slot"
                : resource.status === "maintenance"
                  ? "Under maintenance"
                  : resource.status === "unavailable"
                    ? "Unavailable"
                    : "Book slot"}
        </button>
      </div>
    </article>
  );
}

function BookingModal({ resource, onClose, onBooked, notify }) {
  const today = new Date().toISOString().slice(0, 10);
  const [dateValue, setDateValue] = useState(today);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [existing, setExisting] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadAvailability = useCallback(async () => {
    try {
      const data = await api(`/api/resources/${resource.id}/availability`, {
        params: { date: dateValue },
      });
      setExisting(data.bookings);
    } catch {
      setExisting([]);
    }
  }, [resource.id, dateValue]);

  useEffect(() => {
    loadAvailability();
  }, [loadAvailability]);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setSuggestions([]);

    try {
      const data = await api("/api/reservations", {
        method: "POST",
        body: {
          resource_id: resource.id,
          date: dateValue,
          start_time: start,
          end_time: end,
        },
      });

      if (data.reservation.status === "pending") {
        notify("Booking request sent for admin approval.", "info");
      } else {
        notify("Booking confirmed.", "success");
      }

      onBooked();
      onClose();

    } catch (error) {
      setError(error.message);
      setSuggestions(error.payload?.suggestions || []);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title={`Book ${resource.name}`}
      subtitle={
        resource.requires_approval
          ? `${resource.lab} · admin approval required`
          : `${resource.lab} · instant confirmation if available`
      }
      onClose={onClose}
    >
      <form onSubmit={submit}>
        {error && <div className="alert alert-error">{error}</div>}

        {resource.requires_approval && (
          <div className="alert approval-note">
            This resource uses a manual approval queue. Your requested slot is
            temporarily held while the admin decides.
          </div>
        )}

        <label className="field">
          <span>Date</span>
          <input
            type="date"
            min={today}
            value={dateValue}
            onChange={(event) => setDateValue(event.target.value)}
            required
          />
        </label>

        <p className="muted">
            College booking hours: 09:30 AM – 05:00 PM
        </p>

        <div className="field-grid">
          <label className="field">
            <span>Start time</span>
            <input
              type="time"
              value={start}
              onChange={(event) => setStart(event.target.value)}
              required
            />
          </label>

          <label className="field">
            <span>End time</span>
            <input
              type="time"
              value={end}
              onChange={(event) => setEnd(event.target.value)}
              required
            />
          </label>
        </div>

        <div className="availability-box">
          <strong>Existing / pending bookings on {dateValue}</strong>
          <div className="chips">
            {existing.length === 0 ? (
              <span className="muted">No bookings yet.</span>
            ) : (
              existing.map((slot, index) => (
                <span className="chip" key={`${slot.start_time}-${index}`}>
                  {slot.start_time}–{slot.end_time} · {slot.status}
                </span>
              ))
            )}
          </div>
        </div>

        {suggestions.length > 0 && (
          <div className="suggestion-box">
            <strong>Try one of these available slots:</strong>
            <div className="chips">
              {suggestions.map((slot) => (
                <button
                  key={`${slot.start_time}-${slot.end_time}`}
                  type="button"
                  className="chip chip-button"
                  onClick={() => {
                    setStart(slot.start_time);
                    setEnd(slot.end_time);
                    setError("");
                  }}
                >
                  {slot.start_time}–{slot.end_time}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={busy}>
            {busy
              ? "Checking…"
              : resource.requires_approval
                ? "Submit request"
                : "Confirm booking"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function BrowseResources({ notify }) {
  const [resources, setResources] = useState([]);
  const [filterOptions, setFilterOptions] = useState({
    types: [],
    labs: [],
    categories: [],
  });
  const [filters, setFilters] = useState({
    q: "",
    type: "",
    lab: "",
    category: "",
    status: "",
  });
  const [slot, setSlot] = useState({
    date: "",
    start_time: "",
    end_time: "",
    slot_only: false,
  });
  const [loading, setLoading] = useState(true);
  const [bookingFor, setBookingFor] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);

    try {
      const data = await api("/api/resources", {
        params: {
          ...filters,
          ...slot,
          slot_only: slot.slot_only ? "true" : "",
        },
      });
      setResources(data.resources);
    } catch (error) {
      notify(error.message, "error");
    } finally {
      setLoading(false);
    }
  }, [filters, slot, notify]);

  useEffect(() => {
    api("/api/resources/filters")
      .then(setFilterOptions)
      .catch(() => {});
  }, []);

  useEffect(() => {
    const timer = setTimeout(load, 120);
    return () => clearTimeout(timer);
  }, [load]);

  const setFilter = (key) => (event) => {
    setFilters((current) => ({
      ...current,
      [key]: event.target.value,
    }));
  };

  const setSlotField = (key) => (event) => {
    setSlot((current) => ({
      ...current,
      [key]:
        event.target.type === "checkbox"
          ? event.target.checked
          : event.target.value,
    }));
  };

  const slotReady = slot.date && slot.start_time && slot.end_time;

  return (
    <>
      <PageHeader
        eyebrow="STUDENT PORTAL"
        title="Browse resources"
        subtitle="Search equipment, check live status, and reserve conflict-free slots."
      />

      <div className="filter-card">
        <div className="filter-grid">
          <label className="field">
            <span>Search</span>
            <input
              placeholder="Printer, AI lab, camera…"
              value={filters.q}
              onChange={setFilter("q")}
            />
          </label>

          <label className="field">
            <span>Type</span>
            <select value={filters.type} onChange={setFilter("type")}>
              <option value="">All types</option>
              {filterOptions.types.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Lab</span>
            <select value={filters.lab} onChange={setFilter("lab")}>
              <option value="">All labs</option>
              {filterOptions.labs.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Category</span>
            <select value={filters.category} onChange={setFilter("category")}>
              <option value="">All categories</option>
              {filterOptions.categories.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Status</span>
            <select value={filters.status} onChange={setFilter("status")}>
              <option value="">Any status</option>
              <option value="available">Available</option>
              <option value="booked">Booked</option>
              <option value="maintenance">Maintenance</option>
              <option value="unavailable">Unavailable</option>
            </select>
          </label>
        </div>

        <div className="slot-filter">
          <div>
            <strong>Check a specific slot</strong>
            <span>Optional availability filter.</span>
          </div>

          <input
            type="date"
            value={slot.date}
            onChange={setSlotField("date")}
          />
          <input
            type="time"
            value={slot.start_time}
            onChange={setSlotField("start_time")}
          />
          <input
            type="time"
            value={slot.end_time}
            onChange={setSlotField("end_time")}
          />

          <label className="check-row compact">
            <input
              type="checkbox"
              checked={slot.slot_only}
              disabled={!slotReady}
              onChange={setSlotField("slot_only")}
            />
            <span>Only available</span>
          </label>
        </div>
      </div>

      <div className="section-row">
        <strong>{resources.length} resources</strong>
        <span>Pending approvals also hold a slot to prevent double booking.</span>
      </div>

      {loading ? (
        <div className="loading-card">Loading resources…</div>
      ) : resources.length === 0 ? (
        <div className="empty-card">No resources match your filters.</div>
      ) : (
        <div className="resource-grid">
          {resources.map((resource) => (
            <ResourceCard
              key={resource.id}
              resource={resource}
              onBook={setBookingFor}
            />
          ))}
        </div>
      )}

      {bookingFor && (
        <BookingModal
          resource={bookingFor}
          onClose={() => setBookingFor(null)}
          onBooked={load}
          notify={notify}
        />
      )}
    </>
  );
}

function MyBookings({ notify }) {
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api("/api/reservations");
      setReservations(data.reservations);
    } catch (error) {
      notify(error.message, "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  async function cancel(id) {
    if (!window.confirm("Cancel this reservation?")) return;

    try {
      await api(`/api/reservations/${id}`, {
        method: "DELETE",
      });
      notify("Reservation cancelled.", "success");
      load();
    } catch (error) {
      notify(error.message, "error");
    }
  }

  async function checkIn(id) {
    try {
      await api(`/api/reservations/${id}/check-in`, {
        method: "POST",
      });
      notify("Checked in successfully.", "success");
      load();
    } catch (error) {
      notify(error.message, "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="STUDENT PORTAL"
        title="My bookings"
        subtitle="Track pending approvals, confirmations, check-ins, cancellations and no-shows."
      />

      <div className="automation-note">
        <strong>Automatic no-show release:</strong>
        confirmed bookings must be checked in around their start time. If you
        do not check in within the configured grace period, the worker marks the
        reservation as a no-show and releases the slot.
      </div>

      {loading ? (
        <div className="loading-card">Loading bookings…</div>
      ) : reservations.length === 0 ? (
        <div className="empty-card">You have no bookings yet.</div>
      ) : (
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>Resource</th>
                <th>Lab</th>
                <th>Date</th>
                <th>Time</th>
                <th>Status</th>
                <th>Check-in</th>
                <th />
              </tr>
            </thead>

            <tbody>
              {reservations.map((reservation) => (
                <tr key={reservation.id}>
                  <td>
                    <strong>{reservation.resource_name}</strong>
                  </td>
                  <td>{reservation.lab}</td>
                  <td>{reservation.date}</td>
                  <td>
                    {reservation.start_time}–{reservation.end_time}
                  </td>
                  <td>
                    <BookingBadge status={reservation.status} />
                  </td>
                  <td>
                    {reservation.checked_in_at ? (
                      <span className="checked-in">✓ Checked in</span>
                    ) : reservation.status === "confirmed" ? (
                      <button
                        className="btn btn-ghost btn-small"
                        onClick={() => checkIn(reservation.id)}
                      >
                        Check in
                      </button>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>
                    {["pending", "confirmed"].includes(reservation.status) && (
                      <button
                        className="btn btn-danger btn-small"
                        onClick={() => cancel(reservation.id)}
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function Notifications({ notify }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await api("/api/notifications");
      setItems(data.notifications);
    } catch (error) {
      notify(error.message, "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  async function markRead(id) {
    try {
      await api(`/api/notifications/${id}/read`, {
        method: "POST",
      });
      setItems((current) =>
        current.map((item) =>
          item.id === id
            ? { ...item, is_read: true }
            : item
        )
      );
    } catch (error) {
      notify(error.message, "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="ACTIVITY"
        title="Notifications"
        subtitle="Booking confirmations, approvals, reminders, cancellations and maintenance updates."
      />

      {loading ? (
        <div className="loading-card">Loading notifications…</div>
      ) : items.length === 0 ? (
        <div className="empty-card">No notifications yet.</div>
      ) : (
        <div className="notification-list">
          {items.map((item) => (
            <button
              key={item.id}
              className={`notification ${item.is_read ? "read" : ""}`}
              onClick={() => !item.is_read && markRead(item.id)}
            >
              <span className={`notification-dot ${item.kind}`} />
              <span>
                <strong>{item.message}</strong>
                <small>{new Date(item.created_at).toLocaleString()}</small>
              </span>
              {!item.is_read && <em>Mark read</em>}
            </button>
          ))}
        </div>
      )}
    </>
  );
}

function StudentPortal({ user, setUser, onLogout, notify }) {
  const [tab, setTab] = useState("resources");

  const tabs = [
    { key: "resources", label: "Browse resources", icon: "⌕" },
    { key: "bookings", label: "My bookings", icon: "◫" },
    { key: "notifications", label: "Notifications", icon: "◉" },
  ];

  return (
    <AppShell
      user={user}
      tabs={tabs}
      activeTab={tab}
      setActiveTab={setTab}
      onLogout={onLogout}
    >
      {tab === "resources" && <BrowseResources notify={notify} />}
      {tab === "bookings" && <MyBookings notify={notify} />}
      {tab === "notifications" && (
        <Notifications
          notify={notify}
        />
      )}
    </AppShell>
  );
}

function StatCard({ label, value, tone = "" }) {
  return (
    <div className={`stat-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function AdminDashboard({ notify }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    api("/api/dashboard")
      .then(setData)
      .catch((error) => notify(error.message, "error"));
  }, [notify]);

  if (!data) {
    return <div className="loading-card">Building analytics…</div>;
  }

  const maxPeak = Math.max(
    1,
    ...data.peak_hours.map((item) => item.bookings)
  );

  return (
    <>
      <PageHeader
        eyebrow="ADMIN PORTAL"
        title="Utilization dashboard"
        subtitle="Operational view of resources, approvals, no-shows and booking demand."
      />

      <div className="stats-grid stats-grid-expanded">
        <StatCard label="Total resources" value={data.totals.total_resources} />
        <StatCard label="Available now" value={data.totals.available} tone="green" />
        <StatCard label="Currently booked" value={data.totals.booked} tone="red" />
        <StatCard label="Maintenance" value={data.totals.maintenance} tone="amber" />
        <StatCard label="Today's bookings" value={data.totals.todays_bookings} tone="blue" />
        <StatCard label="Pending approvals" value={data.totals.pending_approvals} tone="purple" />
        <StatCard label="No-shows" value={data.totals.no_shows} tone="gray" />
        <StatCard label="Utilization" value={`${data.utilization_rate}%`} />
      </div>

      <div className="analytics-grid">
        <div className="panel">
          <div className="panel-title">
            <h3>Most used resources</h3>
            <span>Confirmed bookings</span>
          </div>

          {data.most_used_resources.map((resource, index) => (
            <div className="rank-row" key={resource.resource_id}>
              <span>
                <b>{String(index + 1).padStart(2, "0")}</b>
                {resource.name}
              </span>
              <strong>{resource.bookings}</strong>
            </div>
          ))}
        </div>

        <div className="panel">
          <div className="panel-title">
            <h3>Least used resources</h3>
            <span>Reallocation opportunity</span>
          </div>

          {data.least_used_resources.map((resource, index) => (
            <div className="rank-row" key={resource.resource_id}>
              <span>
                <b>{String(index + 1).padStart(2, "0")}</b>
                {resource.name}
              </span>
              <strong>{resource.bookings}</strong>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">
          <h3>Peak booking hours</h3>
          <span>{data.total_cancellations} cancellations recorded</span>
        </div>

        {data.peak_hours.length === 0 ? (
          <div className="muted">No booking data yet.</div>
        ) : (
          data.peak_hours.map((item) => (
            <div className="bar-row" key={item.hour}>
              <span>{String(item.hour).padStart(2, "0")}:00</span>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{ width: `${(item.bookings / maxPeak) * 100}%` }}
                />
              </div>
              <strong>{item.bookings}</strong>
            </div>
          ))
        )}
      </div>
    </>
  );
}

const BLANK_RESOURCE = {
  name: "",
  type: "",
  category: "",
  lab: "",
  description: "",
  max_booking_minutes: 180,
  requires_approval: false,
};

function ResourceFormModal({ initial, onClose, onSaved, notify }) {
  const [form, setForm] = useState(
    initial
      ? { ...BLANK_RESOURCE, ...initial }
      : BLANK_RESOURCE
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const update = (key) => (event) => {
    const value =
      event.target.type === "checkbox"
        ? event.target.checked
        : event.target.value;

    setForm((current) => ({
      ...current,
      [key]: value,
    }));
  };

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      if (initial?.id) {
        await api(`/api/resources/${initial.id}`, {
          method: "PUT",
          body: form,
        });
        notify("Resource updated.", "success");
      } else {
        await api("/api/resources", {
          method: "POST",
          body: form,
        });
        notify("Resource added.", "success");
      }

      onSaved();
      onClose();
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title={initial?.id ? "Edit resource" : "Add resource"}
      subtitle="Configure inventory, booking duration and approval behavior."
      onClose={onClose}
    >
      <form onSubmit={submit}>
        {error && <div className="alert alert-error">{error}</div>}

        <label className="field">
          <span>Name</span>
          <input
            value={form.name}
            onChange={update("name")}
            required
          />
        </label>

        <div className="field-grid">
          <label className="field">
            <span>Type</span>
            <input
              value={form.type}
              onChange={update("type")}
              required
            />
          </label>

          <label className="field">
            <span>Category</span>
            <input
              value={form.category}
              onChange={update("category")}
              required
            />
          </label>
        </div>

        <label className="field">
          <span>Lab / location</span>
          <input
            value={form.lab}
            onChange={update("lab")}
            required
          />
        </label>

        <label className="field">
          <span>Description</span>
          <textarea
            rows="3"
            value={form.description}
            onChange={update("description")}
          />
        </label>

        <label className="field">
          <span>Maximum booking duration (minutes)</span>
          <input
            type="number"
            min="15"
            step="15"
            value={form.max_booking_minutes}
            onChange={update("max_booking_minutes")}
            required
          />
        </label>

        <label className="check-row approval-switch">
          <input
            type="checkbox"
            checked={form.requires_approval}
            onChange={update("requires_approval")}
          />
          <span>
            Require manual admin approval before this resource is confirmed
          </span>
        </label>

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "Saving…" : "Save resource"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ManageResources({ notify }) {
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(undefined);

  const load = useCallback(async () => {
    setLoading(true);

    try {
      const data = await api("/api/resources");
      setResources(data.resources);
    } catch (error) {
      notify(error.message, "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  async function setStatus(resource, status) {
    try {
      await api(`/api/resources/${resource.id}`, {
        method: "PUT",
        body: { status },
      });
      notify(`${resource.name} marked ${status}.`, "success");
      load();
    } catch (error) {
      notify(error.message, "error");
    }
  }

  async function remove(resource) {
    if (!window.confirm(`Delete ${resource.name} and its booking records?`)) {
      return;
    }

    try {
      await api(`/api/resources/${resource.id}`, {
        method: "DELETE",
      });
      notify("Resource removed.", "success");
      load();
    } catch (error) {
      notify(error.message, "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="ADMIN PORTAL"
        title="Resource management"
        subtitle="Maintain inventory, status, booking limits and approval requirements."
        action={
          <button className="btn btn-primary" onClick={() => setEditing(null)}>
            + Add resource
          </button>
        }
      />

      {loading ? (
        <div className="loading-card">Loading resources…</div>
      ) : (
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>Resource</th>
                <th>Type</th>
                <th>Lab</th>
                <th>Approval</th>
                <th>Live status</th>
                <th>Admin status</th>
                <th />
              </tr>
            </thead>

            <tbody>
              {resources.map((resource) => (
                <tr key={resource.id}>
                  <td>
                    <strong>{resource.name}</strong>
                  </td>
                  <td>{resource.type}</td>
                  <td>{resource.lab}</td>
                  <td>
                    {resource.requires_approval ? (
                      <span className="approval-tag">REQUIRED</span>
                    ) : (
                      <span className="muted">Instant</span>
                    )}
                  </td>
                  <td>
                    <StatusPill status={resource.status} />
                  </td>
                  <td>
                    <select
                      value={resource.admin_status}
                      onChange={(event) =>
                        setStatus(resource, event.target.value)
                      }
                    >
                      <option value="available">Available</option>
                      <option value="maintenance">Maintenance</option>
                      <option value="unavailable">Unavailable</option>
                    </select>
                  </td>
                  <td>
                    <div className="row-actions">
                      <button
                        className="btn btn-ghost btn-small"
                        onClick={() => setEditing(resource)}
                      >
                        Edit
                      </button>
                      <button
                        className="btn btn-danger btn-small"
                        onClick={() => remove(resource)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing !== undefined && (
        <ResourceFormModal
          initial={editing}
          onClose={() => setEditing(undefined)}
          onSaved={load}
          notify={notify}
        />
      )}
    </>
  );
}

function ApprovalQueue({ notify }) {
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api("/api/approvals");
      setReservations(data.reservations);
    } catch (error) {
      notify(error.message, "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  async function decide(id, action) {
    try {
      await api(`/api/reservations/${id}/${action}`, {
        method: "POST",
      });
      notify(
        action === "approve"
          ? "Reservation approved."
          : "Reservation rejected.",
        action === "approve" ? "success" : "info"
      );
      load();
    } catch (error) {
      notify(error.message, "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="ADMIN PORTAL"
        title="Approval queue"
        subtitle="Review booking requests for resources configured to require manual approval."
      />

      <div className="automation-note">
        Pending requests temporarily hold their requested slot, so another user
        cannot take the same time while the admin is deciding.
      </div>

      {loading ? (
        <div className="loading-card">Loading approval queue…</div>
      ) : reservations.length === 0 ? (
        <div className="empty-card">No pending approvals. Queue clear.</div>
      ) : (
        <div className="approval-list">
          {reservations.map((reservation) => (
            <article className="approval-card" key={reservation.id}>
              <div>
                <div className="approval-meta">
                  REQUEST #{String(reservation.id).padStart(4, "0")}
                </div>
                <h3>{reservation.resource_name}</h3>
                <p>
                  <strong>{reservation.user_name}</strong> · {reservation.lab}
                </p>
                <p>
                  {reservation.date} · {reservation.start_time}–
                  {reservation.end_time}
                </p>
              </div>

              <div className="approval-actions">
                <button
                  className="btn btn-danger"
                  onClick={() => decide(reservation.id, "reject")}
                >
                  Reject
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => decide(reservation.id, "approve")}
                >
                  Approve
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}

function ManageReservations({ notify }) {
  const [reservations, setReservations] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);

    try {
      const data = await api("/api/reservations", {
        params: { status },
      });
      setReservations(data.reservations);
    } catch (error) {
      notify(error.message, "error");
    } finally {
      setLoading(false);
    }
  }, [status, notify]);

  useEffect(() => {
    load();
  }, [load]);

  async function cancel(id) {
    if (!window.confirm("Cancel this reservation as admin?")) return;

    try {
      await api(`/api/reservations/${id}`, {
        method: "DELETE",
      });
      notify("Reservation cancelled.", "success");
      load();
    } catch (error) {
      notify(error.message, "error");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="ADMIN PORTAL"
        title="Reservations"
        subtitle="Monitor confirmed, pending, cancelled, rejected and no-show bookings."
      />

      <div className="compact-filter">
        <label className="field">
          <span>Status</span>
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">All reservations</option>
            <option value="pending">Pending</option>
            <option value="confirmed">Confirmed</option>
            <option value="rejected">Rejected</option>
            <option value="cancelled">Cancelled</option>
            <option value="no_show">No-show</option>
          </select>
        </label>
      </div>

      {loading ? (
        <div className="loading-card">Loading reservations…</div>
      ) : reservations.length === 0 ? (
        <div className="empty-card">No reservations found.</div>
      ) : (
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>Student</th>
                <th>Resource</th>
                <th>Lab</th>
                <th>Date</th>
                <th>Time</th>
                <th>Status</th>
                <th>Check-in</th>
                <th />
              </tr>
            </thead>

            <tbody>
              {reservations.map((reservation) => (
                <tr key={reservation.id}>
                  <td>{reservation.user_name}</td>
                  <td>
                    <strong>{reservation.resource_name}</strong>
                  </td>
                  <td>{reservation.lab}</td>
                  <td>{reservation.date}</td>
                  <td>
                    {reservation.start_time}–{reservation.end_time}
                  </td>
                  <td>
                    <BookingBadge status={reservation.status} />
                  </td>
                  <td>
                    {reservation.checked_in_at ? (
                      <span className="checked-in">✓ Yes</span>
                    ) : (
                      <span className="muted">No</span>
                    )}
                  </td>
                  <td>
                    {["pending", "confirmed"].includes(reservation.status) && (
                      <button
                        className="btn btn-danger btn-small"
                        onClick={() => cancel(reservation.id)}
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function AdminPortal({ user, setUser, onLogout, notify }) {
  const [tab, setTab] = useState("dashboard");

  const tabs = [
    { key: "dashboard", label: "Dashboard", icon: "▦" },
    { key: "approvals", label: "Approval queue", icon: "✓" },
    { key: "resources", label: "Resources", icon: "◇" },
    { key: "reservations", label: "Reservations", icon: "◫" },
    { key: "notifications", label: "Notifications", icon: "◉" },
  ];

  return (
    <AppShell
      user={user}
      tabs={tabs}
      activeTab={tab}
      setActiveTab={setTab}
      onLogout={onLogout}
    >
      {tab === "dashboard" && <AdminDashboard notify={notify} />}
      {tab === "approvals" && <ApprovalQueue notify={notify} />}
      {tab === "resources" && <ManageResources notify={notify} />}
      {tab === "reservations" && <ManageReservations notify={notify} />}
      {tab === "notifications" && (
        <Notifications
          notify={notify}
        />
      )}
    </AppShell>
  );
}

export default function App() {
  const [user, setUser] = useState(undefined);
  const [toasts, setToasts] = useState([]);

  const notify = useCallback((message, kind = "info") => {
    const id = `${Date.now()}-${Math.random()}`;

    setToasts((current) => [
      ...current,
      { id, message, kind },
    ]);

    window.setTimeout(() => {
      setToasts((current) =>
        current.filter((item) => item.id !== id)
      );
    }, 3400);
  }, []);

  useEffect(() => {
    api("/api/auth/me")
      .then((data) => setUser(data.user))
      .catch(() => setUser(null));
  }, []);

  async function logout() {
    try {
      await api("/api/auth/logout", {
        method: "POST",
      });
    } catch {
      // UI session can still be cleared.
    }

    setUser(null);
  }

  const content = useMemo(() => {
    if (user === undefined) {
      return (
        <div className="boot-screen">
          <div className="brand">
            <span className="brand-dot" />
            CampusFlow
          </div>
          <p>Loading campus resources…</p>
        </div>
      );
    }

    if (!user) {
      return (
        <AuthScreen
          onAuthed={setUser}
          notify={notify}
        />
      );
    }

    return user.role === "admin" ? (
      <AdminPortal
        user={user}
        setUser={setUser}
        onLogout={logout}
        notify={notify}
      />
    ) : (
      <StudentPortal
        user={user}
        setUser={setUser}
        onLogout={logout}
        notify={notify}
      />
    );
  }, [user, notify]);

  return (
    <>
      {content}
      <Toasts items={toasts} />
    </>
  );
}
