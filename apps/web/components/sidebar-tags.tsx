const tags = ["AI", "指数增强", "量化", "新能源", "机器人"];

type Props = {
  active: string | null;
  onChange: (value: string | null) => void;
};

export default function SidebarTags({ active, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {tags.map((tag) => (
        <button
          key={tag}
          className={`rounded-full border px-3 py-1 text-xs ${
            active === tag
              ? "border-[#ef7f52] bg-[#fff7f3] text-[#ef7f52]"
              : "border-[#e2e8f0] text-[#64748b]"
          }`}
          onClick={() => onChange(active === tag ? null : tag)}
        >
          {tag}
        </button>
      ))}
    </div>
  );
}
