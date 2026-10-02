// Henry Harlow: sample-order event for Meta and Pinterest.
//
// Paste into Shopify admin > Settings > Customer events > Add custom pixel.
// Permission: "Required" with Marketing ticked. Data sale: "Data collected
// qualifies as data sale".
//
// The official "Facebook & Instagram" and "Pinterest" apps already send page
// views, product views, add to cart, checkout and purchase (browser and
// server side). This pixel sends the one event they cannot tell apart: a
// completed order that contains samples. Samples are the step before a full
// floor order, so this is the event to optimise and build audiences on while
// purchase volume is still low.

const META_PIXEL_ID = ''; // Events Manager > Data sources > the pixel's ID
const PINTEREST_TAG_ID = ''; // Ads > Conversions > Tag manager > tag ID
const SAMPLE_PATTERN = /sample/i; // matches the sample variant's title

/* eslint-disable */
!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
document,'script','https://connect.facebook.net/en_US/fbevents.js');
!function(e){if(!window.pintrk){window.pintrk=function(){window.pintrk.queue.push(
Array.prototype.slice.call(arguments))};var n=window.pintrk;n.queue=[],n.version="3.0";
var t=document.createElement("script");t.async=!0,t.src=e;var r=document.getElementsByTagName(
"script")[0];r.parentNode.insertBefore(t,r)}}("https://s.pinimg.com/ct/core.js");
/* eslint-enable */

if (META_PIXEL_ID) fbq('init', META_PIXEL_ID);
if (PINTEREST_TAG_ID) pintrk('load', PINTEREST_TAG_ID);

const isSample = (item) =>
  SAMPLE_PATTERN.test(item.variant?.title || '') || SAMPLE_PATTERN.test(item.title || '');

analytics.subscribe('checkout_completed', (event) => {
  const checkout = event.data.checkout;
  const samples = (checkout.lineItems || []).filter(isSample);
  if (!samples.length) return;

  const eventId = `sample-${checkout.order?.id || checkout.token}`;
  const currency = checkout.currencyCode;
  const value = samples.reduce(
    (sum, item) => sum + Number(item.variant?.price?.amount || 0) * item.quantity, 0);
  // Feed items are box variants, so match on the product (item_group_id),
  // not on the sample variant, which the feeds leave out.
  const productIds = samples.map((item) => String(item.variant?.product?.id));

  if (META_PIXEL_ID) {
    fbq('trackCustom', 'SampleOrder', {
      value,
      currency,
      content_ids: productIds,
      content_type: 'product_group',
      num_items: samples.reduce((n, item) => n + item.quantity, 0),
    }, { eventID: eventId });
  }

  if (PINTEREST_TAG_ID) {
    pintrk('track', 'lead', {
      event_id: eventId,
      lead_type: 'Sample',
      value,
      currency,
      line_items: samples.map((item) => ({
        product_id: String(item.variant?.product?.id),
        product_variant_id: String(item.variant?.id),
        product_name: item.title,
        product_price: Number(item.variant?.price?.amount || 0),
        product_quantity: item.quantity,
      })),
    });
  }
});
