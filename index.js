require('dotenv').config()
const { spawn, exec  } = require('node:child_process');
const axios = require('axios');
const cron = require('node-cron');

var proc = null;

async function get_video() {
	try {
		//const q = "🔴 24/7 LIVE: Cat TV for Cats to Watch 😺 Cute Birds Chipmunks Squirrels in the Forest 4K";
		const q = "🔴 24/7 LIVE: Cat TV ";
		const url = `https://youtube.googleapis.com/youtube/v3/search?key=${process.env.YOUTUBE_API_KEY}&part=snippet&q=${encodeURIComponent(q)}`;
		const resp = await axios.get(url);
		const options = resp.data.items.map( (item) => { return { title: item.snippet.title, id: item.id.videoId }});
		const n = ~~(Math.random() * options.length)
		return options[n];
	} catch(error) {
		if (error.response) {
			console.log(`Error code ${error.response.status}`);
			console.log(error.response.data);
		} else if (error.request) {
			console.log(error.request);
		} else {
			console.log('Error', error.message);
		}
	}
}

async function start() {
	const video = await get_video();
	console.log(`starting ${video.id}`);
	const url = `https://www.youtube.com/embed/${video.id}?autoplay=1`;
	proc = spawn('chromium-browser', ['--kiosk', '--autoplay-policy=no-user-gesture-required', url]);
	proc.stdout.on('data', (data) => {
		console.log(`stdout: ${data}`);
	});

	proc.stderr.on('data', (data) => {
		console.error(`stderr: ${data}`);
	});

	proc.on('close', (code) => {
		console.log(`child process exited with code ${code}`);
	}); 
}


async function stop() {
	console.log('killing process');
	if(proc) {
		proc.stdin.pause();
		proc.kill();
		proc = null;
	}
	exec('pkill -o chromium');
}

cron.schedule('*/2 * * * *', start);
cron.schedule('1-59/2 * * * *', stop);



// // Start up the video at 7am
// cron.schedule('0 7 * * *', async () =>  {
// 	const video = await get_video();
// 	console.log(video);
// });

// // Stop the video at 11am
// cron.schedule('0 11 * * *', async () =>  {
// 	const video = await get_video();
// 	console.log(video);
// });

// // Start up the video at 5pm
// cron.schedule('0 17 * * *', async () =>  {
// 	const video = await get_video();
// 	console.log(video);
// });

// // Stop the video at 8pm
// cron.schedule('0 20 * * *', async () =>  {
// 	const video = await get_video();
// 	console.log(video);
// });
