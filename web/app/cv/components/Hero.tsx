import * as React from "react"
import { motion, type Variants } from "framer-motion"
import Image from "next/image"
interface HeroProps {
  illustrationSrc: string
  illustrationAlt?: string
  title: React.ReactNode
  description: string
  buttonText: string
  buttonHref?: string
}

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.14,
    },
  },
}

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.45,
      ease: [0.22, 1, 0.36, 1],
    },
  },
}

export function Hero({
  illustrationSrc,
  illustrationAlt = "Hero Illustration",
  title,
  description,
  buttonText,
  buttonHref = "#",
}: HeroProps) {
  return (
    <section className="relative flex w-full h-full items-center justify-center overflow-hidden bg-background px-4 py-16 md:px-8 md:py-24">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(15,118,110,0.08),transparent_42%),linear-gradient(to_bottom,transparent,rgba(15,23,42,0.03))]" />

      <motion.div
        className="relative mx-auto flex max-w-4xl flex-col items-center text-center"
        initial="hidden"
        animate="show"
        variants={containerVariants}
      >
        <motion.div variants={itemVariants} className="mb-8 rounded-3xl border bg-card/70 p-4 shadow-sm backdrop-blur-sm">
          <Image
            width={288}
            height={215}
            src={illustrationSrc}
            alt={illustrationAlt}
            className="h-auto w-56 select-none md:w-72"
          />
        </motion.div>

        <motion.h1
          variants={itemVariants}
          className="max-w-3xl text-balance text-3xl font-semibold tracking-tight text-foreground md:text-5xl"
        >
          {title}
        </motion.h1>

        <motion.p
          variants={itemVariants}
          className="mt-5 max-w-2xl text-pretty text-sm leading-7 text-muted-foreground md:text-base"
        >
          {description}
        </motion.p>

        {/* <motion.div variants={itemVariants} className="mt-8">
          <Button
            size="lg"
            className="h-10 rounded-full px-5"
          >
            {buttonText}
            <HugeiconsIcon icon={ArrowRight} strokeWidth={1.8} />
          </Button>
        </motion.div> */}
      </motion.div>
    </section>
  )
}

export default Hero
