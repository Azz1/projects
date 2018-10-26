/* Read in jpeg from Raspberry Pi camera captured using 'raspistill --raw' 
   and extract jpeg part and save to file

   Compile: gcc -o readjpg readjpg.c
   Usage: readjpg file-raw.jpg
   Output: file-raw.jpg.jpg
   
   Jack Zhu  25 Oct 2018
*/

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#define LINELEN 256            // how long a string we need to hold the filename
#define RAWBLOCKSIZE 6404096
#define HEADERSIZE 32768
#define ROWSIZE 3264 // number of bytes per row of pixels, including 24 'other' bytes at end
#define IDSIZE 4    // number of bytes in raw header ID string
#define HPIXELS 2592   // number of horizontal pixels on OV5647 sensor
#define VPIXELS 1944   // number of vertical pixels on OV5647 sensor

int main(int argc, char *argv[])
{
FILE *fp, *fpo;  /* input output file */
char fname[LINELEN];    /* filename to open */
char fname1[LINELEN];    /* filename to open */

int i,j,k;       /* loop variables (Hey, I learned FORTRAN early...) */
unsigned long fileLen;  // number of bytes in file
unsigned long offset;  // offset into file to start reading pixel data
unsigned char *buffer;
unsigned short pixel[HPIXELS];  // array holds 16 bits per pixel
unsigned char split;        // single byte with 4 pairs of low-order bits


strcpy(fname, argv[1]);
sprintf(fname1, "%s.jpg", argv[1]);

/* program start */


fp=fopen(fname, "r");
fpo=fopen(fname1, "w");
if (fp==NULL)  {
  fprintf(stderr, "Unable to open %s for input.\n",fname);
  return;
  }
if (fpo==NULL)  {
  fprintf(stderr, "Unable to open %s for output.\n",fname1);
  return;
  }
  // printf("Opening binary file for input: %s\n",fname);

  // for one file, (TotalFileLength:11112983 - RawBlockSize:6404096) + Header:32768 = 4741655
  // The pixel data is arranged in the file in rows, with 3264 bytes per row.
  // with 3264 bytes per row x 1944 rows we have 6345216 bytes, that is the full 2592x1944 image area.
  
	//Get file length
	fseek(fp, 0, SEEK_END);
	fileLen=ftell(fp);
    if (fileLen < RAWBLOCKSIZE) {
      fprintf(stderr, "File %s too short to contain expected 6MB RAW data.\n",fname);
      return;
    }
    offset = (fileLen - RAWBLOCKSIZE) ;  // location in file the raw header starts
    fseek(fp, 0, SEEK_SET);  
  
  //printf("File length = %d bytes.\n",fileLen);
  //printf("offset = %d:",offset);

  //Allocate memory for one line of pixel data
  buffer=(unsigned char *)malloc(offset+1);
  if (!buffer)
  {
    fprintf(stderr, "Memory error!");
    fclose(fp);
    return;
  }

  //Read jpeg data into buffer
  fread(buffer, offset, 1, fp);
  fwrite(buffer, offset, 1, fpo);


  fclose(fp);
  fclose(fpo);
  return 0;
} // end main
