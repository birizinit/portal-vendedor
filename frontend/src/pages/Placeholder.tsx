export default function Placeholder({ title }: { title: string }) {
  return (
    <div className="grid h-full place-items-center">
      <div className="text-center">
        <div className="mb-2 text-4xl">🚧</div>
        <h2 className="text-lg font-bold text-slate-700">{title}</h2>
        <p className="text-sm text-slate-500">Em construção — próxima fase do portal.</p>
      </div>
    </div>
  );
}
