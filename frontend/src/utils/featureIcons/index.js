// Curated icon set shared by the storefront "Why Choose" section and the admin
// Features editor. Kept in a neutral module so the storefront never has to
// import an admin page (which would pull the whole admin bundle into the
// shopper's initial download).
import {
  IconShieldCheck, IconTruck, IconRefresh, IconHeadset, IconStar, IconHeart,
  IconGift, IconDiscount2, IconTag, IconPackage, IconAward, IconThumbUp,
  IconClock, IconLock, IconSparkles, IconLeaf,
} from '@tabler/icons-react'

export const FEATURE_ICONS = {
  'shield-check': IconShieldCheck,
  truck: IconTruck,
  refresh: IconRefresh,
  headset: IconHeadset,
  star: IconStar,
  heart: IconHeart,
  gift: IconGift,
  discount: IconDiscount2,
  tag: IconTag,
  package: IconPackage,
  award: IconAward,
  'thumb-up': IconThumbUp,
  clock: IconClock,
  lock: IconLock,
  sparkles: IconSparkles,
  leaf: IconLeaf,
}
