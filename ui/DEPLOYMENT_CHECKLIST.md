# Netlify Deployment Checklist

Use this checklist to deploy the Trading Bot Cockpit to Netlify.

## Pre-Deployment Requirements

### ✅ Supabase Setup

- [ ] Supabase project created
- [ ] Database tables created:
  - [ ] `bot_events`
  - [ ] `bot_latest_snapshot`
  - [ ] `bot_health`
- [ ] RLS policies enabled (SELECT for authenticated users)
- [ ] Realtime enabled for all three tables
- [ ] Auth provider enabled (Email/Magic Link)
- [ ] Collected credentials:
  - [ ] Supabase URL: `https://<project-ref>.supabase.co`
  - [ ] Anon key: `eyJhbGci...`

### ✅ Repository Setup

- [ ] Code pushed to GitHub
- [ ] All files committed
- [ ] `.gitignore` configured properly

## Netlify Deployment Steps

### 1. Create Netlify Site

- [ ] Go to https://app.netlify.com
- [ ] Click "Add new site" → "Import from Git"
- [ ] Select GitHub provider
- [ ] Authorize Netlify to access repository
- [ ] Select `themirrorplatform/trading-bot` repository

### 2. Configure Build Settings

Enter these exact values:

```
Base directory: ui
Build command: npm run build
Publish directory: ui/dist
```

- [ ] Base directory set to `ui`
- [ ] Build command set to `npm run build`
- [ ] Publish directory set to `ui/dist`

### 3. Set Environment Variables

Go to: Site settings → Environment variables → Add variable

Add these variables:

```env
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGci...
VITE_DEFAULT_DEVICE_ID=bot-01
VITE_APP_MODE=cloud
```

- [ ] `VITE_SUPABASE_URL` added
- [ ] `VITE_SUPABASE_ANON_KEY` added
- [ ] `VITE_DEFAULT_DEVICE_ID` added
- [ ] `VITE_APP_MODE` added

### 4. Deploy Site

- [ ] Click "Deploy site"
- [ ] Wait for build to complete (2-3 minutes)
- [ ] Check deploy logs for errors
- [ ] Build successful ✅

### 5. Configure Supabase Redirects

Get your Netlify URL: `https://<random>.netlify.app`

In Supabase:
- [ ] Go to Authentication → URL Configuration
- [ ] Add to "Redirect URLs":
  - [ ] `https://<your-site>.netlify.app/**`
- [ ] Save configuration

### 6. Test Deployment

Open your Netlify site URL and verify:

- [ ] Site loads without errors
- [ ] Login page appears
- [ ] Can request magic link (check email)
- [ ] Can log in successfully
- [ ] Dashboard appears after login
- [ ] No console errors in browser dev tools

### 7. Test Realtime (requires bot running)

With bot running:

- [ ] Health monitor shows bot status
- [ ] Snapshot updates with P&L data
- [ ] Timeline receives events in real-time
- [ ] Refreshing page doesn't break routing
- [ ] Logout works correctly

## Post-Deployment

### Optional: Custom Domain

- [ ] Go to Domain settings in Netlify
- [ ] Click "Add custom domain"
- [ ] Enter your domain name
- [ ] Update DNS records as instructed
- [ ] Wait for DNS propagation (up to 24 hours)
- [ ] SSL certificate auto-provisioned
- [ ] Update Supabase redirect URLs with custom domain

### Security Verification

Double-check these are NOT in Netlify environment:

- [ ] ❌ No `SERVICE_ROLE_KEY`
- [ ] ❌ No `DEVICE_SHARED_SECRET`
- [ ] ❌ No broker API keys
- [ ] ❌ No bot credentials

### Monitoring

- [ ] Netlify deploy notifications enabled
- [ ] Set up Netlify Analytics (optional)
- [ ] Monitor Supabase usage dashboard

## Troubleshooting

### Build Fails

**Check**: Netlify deploy logs for error messages

**Common issues**:
- Missing environment variables
- Wrong base directory
- npm install failures

**Solution**: Verify build settings match checklist exactly

### "Unauthorized" Error

**Check**: Environment variables in Netlify

**Solution**: 
- Verify `VITE_SUPABASE_URL` is correct
- Verify `VITE_SUPABASE_ANON_KEY` is correct
- Redeploy after fixing

### Auth Not Working

**Check**: Supabase Auth settings

**Solution**:
- Enable Email provider in Supabase
- Add Netlify URL to redirect URLs
- Check email spam folder for magic link

### Realtime Not Updating

**Check**: 
- Browser console for errors
- Supabase Realtime status
- RLS policies

**Solution**:
- Enable Realtime for tables in Supabase
- Verify RLS policies allow SELECT
- Check device_id matches bot's device_id

### 404 on Refresh

**Check**: `ui/public/_redirects` file exists

**Solution**: File should contain:
```
/*    /index.html   200
```

## Success Criteria

All these must be true:

✅ Site deploys successfully
✅ No build errors
✅ Login works
✅ Dashboard loads
✅ No console errors
✅ Realtime updates work (when bot running)
✅ No secrets exposed in browser
✅ RLS enforced
✅ Security headers present

## Support

If issues persist:

1. Check [NETLIFY_SETUP.md](./NETLIFY_SETUP.md)
2. Check [README.md](./README.md)
3. Review Netlify deploy logs
4. Check Supabase logs
5. Verify all environment variables

## Resources

- [Netlify Documentation](https://docs.netlify.com)
- [Supabase Documentation](https://supabase.com/docs)
- [Vite Documentation](https://vitejs.dev)
- [React Documentation](https://react.dev)
