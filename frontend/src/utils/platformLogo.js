const PLATFORM_DOMAINS = {
  Ajio: 'ajio.com',
  Amazon: 'amazon.in',
  Blinkit: 'blinkit.com',
  Flipkart: 'flipkart.com',
  Instagram: 'instagram.com',
  Instamart: 'swiggy.com',
  Meesho: 'meesho.com',
  Myntra: 'myntra.com',
  Nykaa: 'nykaa.com',
  'Shopify Store': 'shopify.com',
  Swiggy: 'swiggy.com',
  Zepto: 'zeptonow.com',
  Zomato: 'zomato.com',
}

export function getPlatformLogoUrl(platformName, size = 32) {
  const domain = PLATFORM_DOMAINS[platformName]
  if (!domain) return null
  return `https://www.google.com/s2/favicons?sz=${size}&domain=${domain}`
}
