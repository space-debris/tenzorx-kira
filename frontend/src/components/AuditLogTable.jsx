export default function AuditLogTable({ events = [] }) {
  if (!events.length) {
    return <div className="text-sm text-slate-400">No audit events found.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-slate-50 text-left">
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">When</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Action</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Entity</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Description</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Actor</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {events.map((event) => (
            <tr key={event.id}>
              <td className="px-4 py-3 text-sm text-slate-600">
                {new Date(event.created_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
              </td>
              <td className="px-4 py-3 text-sm font-semibold text-slate-700">{event.action}</td>
              <td className="px-4 py-3 text-sm text-slate-600">{event.entity_type}</td>
              <td className="px-4 py-3 text-sm text-slate-600">{event.description}</td>
              <td className="px-4 py-3 text-sm text-slate-600">{event.actor_name || 'system'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
