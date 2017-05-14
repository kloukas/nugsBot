import discord
import asyncio
import json
import urllib.request
import config
import aiohttp
import objectpath as op

client = discord.Client()
permissions = config.permissions
corpID = config.corpID
killChannelID = config.killChannelID
capChannelID = config.capChannelID
url = "https://redisq.zkillboard.com/listen.php?ttw=2"
kmLoop = []


def formatISK(amount):
    for unit in ['', 'K', 'M']:
        if abs(amount) < 1000:
            return "{:.1f}{} ISK".format(amount, unit)
        amount /= 1000.0
    return "{:.1f}B ISK".format(amount)


async def fetchKM():
    try:
        while not client.is_closed:
            corpKill = False
            r = await aiohttp.request('GET', url)
            t = await r.text()
            r.close()
            data = json.loads(t)
            tree = op.Tree(data)
            if data['package'] is None:
                print('Null')
            else:
                km = data['package']['killmail']
                system = km["solarSystem"]['name']
                shipType = km["victim"]['shipType']
                attackers = tree.execute('$.package.killmail.attackers..corporation[@.id is {}]'.format(corpID))
                victimCorp = tree.execute('$.package.killmail.victim.corporation.id is {}'.format(corpID))
                print("tick")
                if victimCorp or list(attackers):
                    # print("----------------")
                    # print(bool(victimCorp), bool(list(attackers)))
                    # print("----------------")
                    corpKill = True

                # Alert cap fight
                if system in config.systems and shipType['name'] in config.ships:
                    print('Gotcha, Cap Fight')
                    zkillUrl = 'https://zkillboard.com/kill/{}/'.format(km['killID'])
                    iconUrl = 'https://image.eveonline.com/Type/{}_32.png'.format(shipType['id'])
                    capEmbed = discord.Embed(title="Cap Fight", url=zkillUrl)
                    capEmbed.set_thumbnail(url=iconUrl)
                    capEmbed.add_field(name="Ship Type", value=shipType['name'])
                    capEmbed.add_field(name="Location", value=system)
                    capEmbed.add_field(name="Time", value=km['killTime'])
                    chan = client.get_channel(capChannelID)
                    await client.send_message(chan, embed=capEmbed)
                    await client.send_message(
                        chan,
                        '@everyone')

                # Post Corp Kill
                if corpKill:
                    print('Gotcha, Corp Kill/Loss')
                    zkillUrl = 'https://zkillboard.com/kill/{}/'.format(km['killID'])
                    iconUrl = 'https://image.eveonline.com/Type/{}_32.png'.format(shipType['id'])
                    capEmbed = discord.Embed(title="Corp Kill", url=zkillUrl)
                    capEmbed.set_thumbnail(url=iconUrl)
                    capEmbed.add_field(name="Ship Type", value=shipType['name'])
                    capEmbed.add_field(name="Location", value=system)
                    capEmbed.add_field(name="Victim", value=km['victim']['character']['name'])
                    capEmbed.add_field(name="Victim Corp", value=km['victim']['corporation']['name'])
                    capEmbed.add_field(name="Value", value=formatISK(data['package']['zkb']['totalValue']))
                    capEmbed.add_field(name="Attackers", value=km['attackerCount'])
                    capEmbed.add_field(name="Time", value=km['killTime'])
                    await client.send_message(client.get_channel(killChannelID), embed=capEmbed)

            # await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        print("Cancelled")
        await asyncio.sleep(5)


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await client.send_message(client.get_channel(killChannelID), 'Bot Online')


@client.event
async def on_message(message):
    memberRole = message.server.get_member(message.author.id).top_role.name
    if message.content == '!exit':
        if permissions[memberRole] <= 2:
            await client.send_message(message.channel, "Bot closing")
            if kmLoop:
                await client.send_message(message.channel, 'Stopping Loop')
                for loop in kmLoop:
                    loop.cancel()
                del kmLoop[:]
            await client.logout()

    elif message.content == '!startLoop':
        if permissions[memberRole] <= 2:
            if not kmLoop:
                await client.send_message(message.channel, 'Starting Loop')
                kmLoop.append(client.loop.create_task(fetchKM()))
            else:
                await client.send_message(message.channel, 'Loop already running')

    elif message.content == '!stopLoop':
        if permissions[memberRole] <= 2:
            if kmLoop:
                await client.send_message(message.channel, 'Stopping Loop')
                for loop in kmLoop:
                    loop.cancel()
                del kmLoop[:]
            else:
                await client.send_message(message.channel, 'Loop not running')


client.run(config.discordKey)
