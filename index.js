require('dotenv').config()
const axios = require('axios');
const cron = require('node-cron');

//const title = "🔴 24/7 LIVE: Cat TV for Cats to Watch 😺 Cute Birds Chipmunks Squirrels in the Forest 4K";
const q = "🔴 24/7 LIVE: Cat TV ";
const url = `https://youtube.googleapis.com/youtube/v3/search?key=${process.env.YOUTUBE_API_KEY}&part=snippet&q=${encodeURIComponent(q)}`;

async function get_video() {
	try {
		const resp = await axios.get(url);
		const options = resp.data.items.map( (item) => { return { title: item.snippet.title, id: item.id.videoId }});
		const n = ~~(Math.random() * options.length)
		return options[n];
	} catch(error) {
		if (error.response) {
			console.log(error.response.data);
			console.log(error.response.status);
		  } else if (error.request) {
			console.log(error.request);
		  } else {
			console.log('Error', error.message);
		  }
		  //console.log(error.config);
	}
}

cron.schedule('*/2 * * * *', async () =>  {
	const video = await get_video();
	console.log(`starting ${video.title}`);
});

cron.schedule('1-59/2 * * * *', async () =>  {
	console.log(`STOPPING`);
});


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
