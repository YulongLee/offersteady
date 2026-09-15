import { useState } from "react";
import { ArrowUpRightIcon, ChatCircleTextIcon, ScanIcon } from "@phosphor-icons/react";

// Captures of the existing product UI with synthetic, non-customer examples.
const examples = [
  {
    id: "project",
    label: "项目追问",
    image: "/media/homepage/project-demo.png",
    alt: "面试稳项目追问演示：左侧实时对话，右侧结合简历与岗位资料整理回答建议",
    title: "把项目经历，变成有条理的回答。",
    detail: "结合简历与岗位资料，整理回答建议。",
    Icon: ChatCircleTextIcon,
  },
  {
    id: "screenshot",
    label: "截图问题",
    image: "/media/homepage/screenshot-demo.png",
    alt: "面试稳截图问题演示：识别系统设计题，并展示分析路径和回答建议",
    title: "遇到截图题，也能找到切入点。",
    detail: "通过电脑助手截图，在网页查看回答建议。",
    Icon: ScanIcon,
  },
] as const;

export function HomepageProductPreview() {
  const [selected, setSelected] = useState(0);
  const example = examples[selected]!;
  return <figure className="cn-product-preview" aria-label="产品界面演示">
    <div className="cn-preview-toolbar">
      <div className="cn-preview-switch" role="group" aria-label="选择演示场景">
        {examples.map((item, index) => <button type="button" key={item.id} aria-pressed={selected === index} onClick={() => setSelected(index)}>
          <item.Icon size={17} aria-hidden="true" />{item.label}
        </button>)}
      </div>
      <a className="cn-preview-expand" href={example.image} target="_blank" rel="noreferrer" aria-label={`查看${example.label}演示大图`}>查看大图<ArrowUpRightIcon size={16} aria-hidden="true" /></a>
    </div>
    <a className="cn-preview-image" href={example.image} target="_blank" rel="noreferrer" aria-label={`打开${example.label}完整界面`}>
      <img src={example.image} alt={example.alt} width={3840} height={2160} decoding="async" />
    </a>
    <figcaption>
      <div aria-live="polite"><strong>{example.title}</strong><p>{example.detail}</p></div>
      <span>产品界面 · 合成示例 · 回答区域局部展示</span>
    </figcaption>
  </figure>;
}
