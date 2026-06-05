"use client"
import Hero from "./components/Hero"


export default function CVPage() {

  return (
    <Hero
      illustrationSrc="/image.png"
      illustrationAlt="候选人简历分析工作台插画"
      title="自动化处理 CV"
      description="面向招聘筛选场景的 CV 工作台：上传 PDF 后，系统会自动抽取结构化信息，结合岗位要求完成核验、匹配评分，并生成可直接用于面试的分层题目。"
      buttonText="开始处理 CV"
      buttonHref="/cv"
    />
  )
}
